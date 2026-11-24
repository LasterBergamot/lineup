"""Business rules for players, between the router and the repository.

The main rule: a player always sits on the roster of a team the caller belongs to. A `team_id` that
is unknown *or* belongs to a team the caller is not in is a 404 "Team not found" (the API never
confirms that someone else's team exists); it also keeps a bad id from failing the foreign key at
commit time as an opaque 500.

The second rule (#284): the NSSZ number is a player's identity, so a team's roster holds each one
once (compared trimmed, which the schema does, and case-insensitively). Creating or updating a
player onto a number already on the roster is a 409 with a fixed, generic body: it never echoes
the other player's record (NSSZ numbers are personal data) and nothing here logs a number. The
service checks first for a friendly answer; the unique index `ux_players_team_nssz` is what holds
under concurrency, and a request that loses the race is turned into the same 409.
"""

from __future__ import annotations

import uuid
from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player
from lineup.players import repository
from lineup.teams import repository as team_repo


async def _ensure_member_of_team(
    session: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    team = await team_repo.get_team(session, team_id=team_id, user_id=user_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")


_DUPLICATE_NSSZ = "A player with this NSSZ number is already on this team"


async def _ensure_nssz_free(
    session: AsyncSession,
    team_id: uuid.UUID,
    nssz_number: str,
    exclude_player_id: uuid.UUID | None = None,
) -> None:
    """Raise 409 with a generic message if the team's roster already has this NSSZ number."""
    if await repository.nssz_taken(
        session,
        team_id=team_id,
        nssz_number=nssz_number,
        exclude_player_id=exclude_player_id,
    ):
        raise HTTPException(status_code=409, detail=_DUPLICATE_NSSZ)


async def _reraise_as_duplicate(
    session: AsyncSession,
    error: IntegrityError,
    team_id: uuid.UUID,
    nssz_number: str,
    exclude_player_id: uuid.UUID | None = None,
) -> NoReturn:
    """Handle an `IntegrityError` from a player write: roll back, and if the cause is the
    unique NSSZ index (a concurrent request won the race the pre-check cannot see) raise the same
    409 as the pre-check. Any other integrity error is re-raised unchanged for the app-wide
    handler. Looks the cause up instead of parsing the driver's message, which differs between
    SQLite and Postgres and quotes the values."""
    await session.rollback()
    await _ensure_nssz_free(session, team_id, nssz_number, exclude_player_id)
    raise error


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    user_id: uuid.UUID,
    team_id: uuid.UUID,
) -> Player:
    """Create a player on `team_id`'s roster. Raises 404 "Team not found" unless the caller is a
    member of that team, and 409 if the roster already has this NSSZ number (also when a
    concurrent request inserted it first)."""
    await _ensure_member_of_team(session, team_id, user_id)
    await _ensure_nssz_free(session, team_id, nssz_number)
    try:
        return await repository.create_player(
            session,
            name=name,
            nssz_number=nssz_number,
            created_by=user_id,
            team_id=team_id,
        )
    except IntegrityError as error:
        await _reraise_as_duplicate(session, error, team_id, nssz_number)


async def get_player_or_404(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Player:
    """Return the player or raise 404 "Player not found" (also for another team's player)."""
    player = await repository.get_player(session, player_id=player_id, user_id=user_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


async def list_players(
    session: AsyncSession,
    user_id: uuid.UUID,
    team_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Player], int]:
    """One page of the players of the caller's teams (optionally one team) and the total count."""
    return await repository.list_players(
        session, user_id=user_id, team_id=team_id, limit=limit, offset=offset
    )


async def update_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    name: str,
    nssz_number: str,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Player:
    """Replace a player's fields, possibly moving them to another of the caller's teams. Raises
    404 if the player, or the target team, is not reachable for the caller, and 409 if another
    player on the target roster already has this NSSZ number (the player itself does not count,
    so saving a name change with the same number works)."""
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await _ensure_member_of_team(session, team_id, user_id)
    await _ensure_nssz_free(session, team_id, nssz_number, exclude_player_id=player.id)
    try:
        return await repository.update_player(
            session, player=player, name=name, nssz_number=nssz_number, team_id=team_id
        )
    except IntegrityError as error:
        await _reraise_as_duplicate(
            session, error, team_id, nssz_number, exclude_player_id=player_id
        )


async def delete_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a player; always allowed for team members, because saved lineups store copies.
    404 if unreachable."""
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await repository.delete_player(session, player=player)
