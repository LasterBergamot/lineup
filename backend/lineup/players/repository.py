"""Database access for players: the only place that writes player queries.

A player belongs to a team's roster, and every member of that team may use it. So each query here
is keyed by the signed-in `user_id` and restricted to players whose team the user belongs to
(`team_repo.member_team_ids`); lookups return `None` when nothing matches, which the service
turns into a 404.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player
from lineup.teams.repository import member_team_ids


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    created_by: uuid.UUID,
    team_id: uuid.UUID,
) -> Player:
    """Insert a player, commit, and return it refreshed. The caller must have checked that
    `created_by` belongs to `team_id`."""
    player = Player(
        id=uuid.uuid4(),
        name=name,
        nssz_number=nssz_number,
        created_by=created_by,
        team_id=team_id,
    )
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def nssz_taken(
    session: AsyncSession,
    team_id: uuid.UUID,
    nssz_number: str,
    exclude_player_id: uuid.UUID | None = None,
) -> bool:
    """True if `team_id`'s roster already holds `nssz_number`, ignoring case, optionally not
    counting the player `exclude_player_id` (the one being edited). Uses SQL `lower()` on both
    sides, exactly like the unique index `ux_players_team_nssz`, so the check and the index never
    disagree about what "the same" means. Only a boolean leaves this function: the other player's
    record is never returned, let alone logged."""
    query = select(Player.id).where(
        Player.team_id == team_id,
        func.lower(Player.nssz_number) == func.lower(nssz_number),
    )
    if exclude_player_id is not None:
        query = query.where(Player.id != exclude_player_id)
    return (await session.execute(query.limit(1))).first() is not None


async def get_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Player | None:
    """Fetch one player on the roster of a team `user_id` belongs to. Returns `None` if the
    player doesn't exist or belongs to a team the user is not in."""
    result = await session.execute(
        select(Player).where(
            Player.id == player_id, Player.team_id.in_(member_team_ids(user_id))
        )
    )
    return result.scalar_one_or_none()


async def list_players(
    session: AsyncSession,
    user_id: uuid.UUID,
    team_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Player], int]:
    """One page of the players of all teams `user_id` belongs to (optionally one team), ordered
    by `(created_at, id)` so paging is stable, plus the total count before paging. Filtering by a
    team the user is not in yields an empty page."""
    query = select(Player).where(Player.team_id.in_(member_team_ids(user_id)))
    if team_id is not None:
        query = query.where(Player.team_id == team_id)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    query = query.order_by(Player.created_at, Player.id).limit(limit).offset(offset)
    items = list((await session.execute(query)).scalars().all())
    return items, total


async def update_player(
    session: AsyncSession,
    player: Player,
    name: str,
    nssz_number: str,
    team_id: uuid.UUID,
) -> Player:
    """Overwrite name, NSSZ number and team of a player, commit, and return it refreshed."""
    player.name = name
    player.nssz_number = nssz_number
    player.team_id = team_id
    await session.commit()
    await session.refresh(player)
    return player


async def delete_player(
    session: AsyncSession,
    player: Player,
) -> None:
    """Delete a player. Saved lineups are unaffected (their snapshots only lose the soft reference)."""
    await session.delete(player)
    await session.commit()
