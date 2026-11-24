"""Database access for team staff: the only place that writes staff queries.

Staff belong to a team and every member of the team may use them. These functions do not check
membership themselves: the service has already proven the caller is in `team_id` (via
`teams.repository.get_team`), and every lookup here is additionally keyed by `team_id`, so a
staff id of another team is simply not found.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player, TeamStaff


async def player_on_roster(
    session: AsyncSession, team_id: uuid.UUID, player_id: uuid.UUID
) -> bool:
    """True if `player_id` is a player on `team_id`'s roster. Only a boolean leaves here."""
    query = select(Player.id).where(Player.id == player_id, Player.team_id == team_id)
    return (await session.execute(query.limit(1))).first() is not None


async def list_staff(session: AsyncSession, team_id: uuid.UUID) -> list[TeamStaff]:
    """All staff entries of a team, ordered by `(created_at, id)` so the order is stable."""
    result = await session.execute(
        select(TeamStaff)
        .where(TeamStaff.team_id == team_id)
        .order_by(TeamStaff.created_at, TeamStaff.id)
    )
    return list(result.scalars().all())


async def get_staff(
    session: AsyncSession, team_id: uuid.UUID, staff_id: uuid.UUID
) -> TeamStaff | None:
    """One staff entry of `team_id`, or `None` if it does not exist or belongs to another team."""
    result = await session.execute(
        select(TeamStaff).where(TeamStaff.id == staff_id, TeamStaff.team_id == team_id)
    )
    return result.scalar_one_or_none()


async def _clear_default(
    session: AsyncSession,
    team_id: uuid.UUID,
    role: str,
    except_id: uuid.UUID | None,
) -> None:
    """Un-default the team's current default for `role` (other than `except_id`), without
    committing. Must run *before* the new default is flushed, or the partial unique index would
    see two defaults at once."""
    statement = (
        update(TeamStaff)
        .where(
            TeamStaff.team_id == team_id,
            TeamStaff.role == role,
            TeamStaff.is_default.is_(True),
        )
        .values(is_default=False)
        .execution_options(synchronize_session=False)
    )
    if except_id is not None:
        statement = statement.where(TeamStaff.id != except_id)
    await session.execute(statement)


async def create_staff(
    session: AsyncSession,
    team_id: uuid.UUID,
    created_by: uuid.UUID,
    role: str,
    name: str,
    source_player_id: uuid.UUID | None,
    is_default: bool,
) -> TeamStaff:
    """Insert a staff entry, commit, and return it refreshed. With `is_default`, the role's
    previous default is cleared in the same transaction, so a team never has two."""
    if is_default:
        await _clear_default(session, team_id, role, except_id=None)
    staff = TeamStaff(
        id=uuid.uuid4(),
        team_id=team_id,
        created_by=created_by,
        role=role,
        name=name,
        source_player_id=source_player_id,
        is_default=is_default,
    )
    session.add(staff)
    await session.commit()
    await session.refresh(staff)
    return staff


async def update_staff(
    session: AsyncSession,
    staff: TeamStaff,
    role: str,
    name: str,
    source_player_id: uuid.UUID | None,
    is_default: bool,
) -> TeamStaff:
    """Overwrite every editable field, commit, and return the entry refreshed. With
    `is_default`, the other default of the (new) role is cleared in the same transaction."""
    if is_default:
        await _clear_default(session, staff.team_id, role, except_id=staff.id)
    staff.role = role
    staff.name = name
    staff.source_player_id = source_player_id
    staff.is_default = is_default
    await session.commit()
    await session.refresh(staff)
    return staff


async def delete_staff(session: AsyncSession, staff: TeamStaff) -> None:
    """Delete a staff entry. Nothing refers to it, and no other default is promoted."""
    await session.delete(staff)
    await session.commit()
