"""Business rules for team staff, between the router and the repository.

Staff are a team entity: any member of the team may list, add, change and delete them. A team the
caller is not in, and a `source_player_id` that is not a player of *this* team's roster, are both
404 (the API never confirms that someone else's row exists); a staff id of another team is 404
too. Setting a new default for a role replaces the old one atomically (see the repository), and
the partial unique index decides a concurrent race: the loser gets the app-wide 409. Nothing
here logs a name.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import TeamStaff
from lineup.staff import repository
from lineup.staff.schemas import StaffWrite
from lineup.teams import repository as team_repo


async def _ensure_member_of_team(
    session: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    team = await team_repo.get_team(session, team_id=team_id, user_id=user_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")


async def _ensure_source_player(
    session: AsyncSession, team_id: uuid.UUID, source_player_id: uuid.UUID | None
) -> None:
    """Raise 404 "Player not found" unless the id is empty or a player on this team's roster."""
    if source_player_id is None:
        return
    if not await repository.player_on_roster(session, team_id, source_player_id):
        raise HTTPException(status_code=404, detail="Player not found")


async def list_staff(
    session: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> list[TeamStaff]:
    """The team's staff entries. 404 "Team not found" unless the caller is a member."""
    await _ensure_member_of_team(session, team_id, user_id)
    return await repository.list_staff(session, team_id)


async def create_staff(
    session: AsyncSession,
    team_id: uuid.UUID,
    body: StaffWrite,
    user_id: uuid.UUID,
) -> TeamStaff:
    """Add a staff entry to the team. 404 for a team the caller is not in or a
    `source_player_id` outside the team's roster. With `is_default` it replaces the role's
    previous default."""
    await _ensure_member_of_team(session, team_id, user_id)
    await _ensure_source_player(session, team_id, body.source_player_id)
    return await repository.create_staff(
        session,
        team_id=team_id,
        created_by=user_id,
        role=body.role.value,
        name=body.name,
        source_player_id=body.source_player_id,
        is_default=body.is_default,
    )


async def _get_staff_or_404(
    session: AsyncSession, team_id: uuid.UUID, staff_id: uuid.UUID, user_id: uuid.UUID
) -> TeamStaff:
    await _ensure_member_of_team(session, team_id, user_id)
    staff = await repository.get_staff(session, team_id, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return staff


async def update_staff(
    session: AsyncSession,
    team_id: uuid.UUID,
    staff_id: uuid.UUID,
    body: StaffWrite,
    user_id: uuid.UUID,
) -> TeamStaff:
    """Replace a staff entry's role, name, source player and default flag. 404 for an
    unreachable team, a staff id that is not on that team, or a foreign `source_player_id`."""
    staff = await _get_staff_or_404(session, team_id, staff_id, user_id)
    await _ensure_source_player(session, team_id, body.source_player_id)
    return await repository.update_staff(
        session,
        staff=staff,
        role=body.role.value,
        name=body.name,
        source_player_id=body.source_player_id,
        is_default=body.is_default,
    )


async def delete_staff(
    session: AsyncSession,
    team_id: uuid.UUID,
    staff_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a staff entry (404 if unreachable). If it was the default of its role, the role
    simply has no default afterwards."""
    staff = await _get_staff_or_404(session, team_id, staff_id, user_id)
    await repository.delete_staff(session, staff=staff)
