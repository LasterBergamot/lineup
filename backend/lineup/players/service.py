"""Business rules for players, between the router and the repository.

The main rule: a player always sits on the roster of a team the caller belongs to. A `team_id` that
is unknown *or* belongs to a team the caller is not in is a 404 "Team not found" (the API never
confirms that someone else's team exists); it also keeps a bad id from failing the foreign key at
commit time as an opaque 500.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
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


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    user_id: uuid.UUID,
    team_id: uuid.UUID,
) -> Player:
    """Create a player on `team_id`'s roster. Raises 404 "Team not found" unless the caller is a
    member of that team."""
    await _ensure_member_of_team(session, team_id, user_id)
    return await repository.create_player(
        session,
        name=name,
        nssz_number=nssz_number,
        created_by=user_id,
        team_id=team_id,
    )


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
    404 if the player, or the target team, is not reachable for the caller."""
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await _ensure_member_of_team(session, team_id, user_id)
    return await repository.update_player(
        session, player=player, name=name, nssz_number=nssz_number, team_id=team_id
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
