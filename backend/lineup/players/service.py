"""Business rules for players, between the router and the repository.

The main rule here: a `team_id` must point at a team that exists, otherwise the foreign key would
fail at commit time as an opaque 500.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player
from lineup.players import repository
from lineup.teams import repository as team_repo


async def _ensure_team_exists(
    session: AsyncSession, team_id: uuid.UUID | None, user_id: uuid.UUID | None
) -> None:
    """Without this an unknown team_id fails the FK at commit time as a 500."""
    if team_id is None:
        return
    team = await team_repo.get_team(session, team_id=team_id, owner_id=user_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
) -> Player:
    """Create a player. Raises 404 "Team not found" if `team_id` is given but unknown."""
    await _ensure_team_exists(session, team_id, user_id)
    return await repository.create_player(
        session, name=name, nssz_number=nssz_number, user_id=user_id, team_id=team_id
    )


async def get_player_or_404(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> Player:
    """Return the player or raise 404 "Player not found"."""
    player = await repository.get_player(session, player_id=player_id, user_id=user_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


async def list_players(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Player], int]:
    """One page of players (optionally for one team) and the total count."""
    return await repository.list_players(
        session, user_id=user_id, team_id=team_id, limit=limit, offset=offset
    )


async def update_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    name: str,
    nssz_number: str,
    team_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> Player:
    """Replace a player's fields. Raises 404 if the player or the given `team_id` is unknown."""
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await _ensure_team_exists(session, team_id, user_id)
    return await repository.update_player(
        session, player=player, name=name, nssz_number=nssz_number, team_id=team_id
    )


async def delete_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> None:
    """Delete a player; always allowed, because saved lineups store copies. 404 if unknown."""
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await repository.delete_player(session, player=player)
