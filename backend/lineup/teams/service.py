"""Business rules for teams, between the router (HTTP) and the repository (SQL).

Raises `HTTPException` directly (there are no custom exception types in this project).

Two different failures, on purpose: a team the caller does not belong to is a `404` (the API never
confirms that someone else's team exists), while a *member* who lacks the `owner` role gets `403`
because they already know the team is there.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Team, TeamMember, TeamRole
from lineup.teams import repository
from lineup.teams.repository import TeamWithRole
from lineup.teams.schemas import MemberResponse, TeamDeleteResponse


async def create_team(
    session: AsyncSession,
    name: str,
    created_by: uuid.UUID,
    is_public: bool,
    display_name: str | None = None,
) -> TeamWithRole:
    """Create a team; its creator becomes its `owner`, listed under `display_name`."""
    team = await repository.create_team(
        session,
        name=name,
        created_by=created_by,
        is_public=is_public,
        display_name=display_name,
    )
    return team, TeamRole.OWNER.value


async def get_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamWithRole:
    """Return the team and the caller's role, or raise 404 "Team not found" (also when the team
    exists but the caller is not a member)."""
    found = await repository.get_team(session, team_id=team_id, user_id=user_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return found


async def get_owned_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Team:
    """Like `get_team_or_404`, but the caller must also be an owner of the team (403 if not)."""
    team, role = await get_team_or_404(session, team_id=team_id, user_id=user_id)
    if role != TeamRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Only a team owner can do this")
    return team


async def list_teams(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
    display_name: str | None = None,
) -> tuple[list[TeamWithRole], int]:
    """One page of the caller's teams (with their role) and the total count.

    Also records the caller's current `display_name` on all their memberships (see
    `repository.refresh_display_name`). The client lists teams every time it starts, so this is
    what fills in members who joined before names were stored, with no re-invite. A token
    without a name leaves the stored one alone.
    """
    if display_name:
        await repository.refresh_display_name(
            session, user_id=user_id, display_name=display_name
        )
    return await repository.list_teams(
        session, user_id=user_id, limit=limit, offset=offset
    )


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    """Search the opponent directory (listed teams only); no membership check by design."""
    return await repository.search_teams_pool(session, search=search, limit=limit)


async def recent_opponents(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int,
) -> list[str]:
    """Opponent names the team used before, newest first. 404 unless the caller is a member."""
    await get_team_or_404(session, team_id=team_id, user_id=user_id)
    return await repository.recent_opponents(session, team_id=team_id, limit=limit)


async def update_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    name: str,
    is_public: bool | None,
    user_id: uuid.UUID,
) -> TeamWithRole:
    """Rename a team and/or list/unlist it in the opponent directory. Owner only."""
    team = await get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    team = await repository.update_team(
        session, team=team, name=name, is_public=is_public
    )
    return team, TeamRole.OWNER.value


async def delete_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamDeleteResponse:
    """Delete a team (owner only). Raises 404/403 as above and 409 while players or saved
    lineups are still in its workspace.

    The pre-checks exist for their friendly messages. The database's `RESTRICT` is the real
    guard: a player added between the check and the delete makes the delete fail, and that is
    reported as the same 409.

    """
    team = await get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    player_count = await repository.count_players_for_team(session, team_id=team.id)
    if player_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete team: it still has {player_count} player(s) on its "
                "roster. Remove or reassign the players before deleting the team."
            ),
        )
    lineup_count = await repository.count_saved_lineups_for_team(
        session, team_id=team.id
    )
    if lineup_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete team: it still has {lineup_count} saved lineup(s). "
                "Delete them before deleting the team."
            ),
        )
    if not await repository.delete_team(session, team=team):
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete team: players or saved lineups were added while it was "
                "being deleted. Remove them and try again."
            ),
        )
    return TeamDeleteResponse(id=team.id, name=team.name, deleted=True)


async def list_members(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[MemberResponse]:
    """The team's members, oldest first, for any member of the team (404 for everyone else)."""
    await get_team_or_404(session, team_id=team_id, user_id=user_id)
    members = await repository.list_members(session, team_id=team_id)
    return [
        MemberResponse(
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at,
            display_name=m.display_name,
            is_you=m.user_id == user_id,
        )
        for m in members
    ]


async def _get_member_or_404(
    session: AsyncSession, team_id: uuid.UUID, member_id: uuid.UUID
) -> TeamMember:
    member = await repository.get_membership(
        session, team_id=team_id, user_id=member_id
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


async def remove_member(
    session: AsyncSession,
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Remove `member_id` from the team: an owner may remove anyone, any member may remove
    themselves (leave). 404 for non-members of the team and for an unknown member, 403 when a
    non-owner tries to remove somebody else, 409 when it would leave the team without an owner.
    """
    _team, role = await get_team_or_404(session, team_id=team_id, user_id=user_id)
    if member_id != user_id and role != TeamRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Only a team owner can do this")
    member = await _get_member_or_404(session, team_id=team_id, member_id=member_id)
    if (
        member.role == TeamRole.OWNER.value
        and await repository.count_owners(session, team_id=team_id) <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail="A team needs an owner: transfer ownership to another member first",
        )
    await repository.remove_member(session, member=member)


async def transfer_ownership(
    session: AsyncSession,
    team_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamWithRole:
    """Hand the team over to another member; the caller (an owner, else 403/404) becomes a plain
    member. 422 if the target is the caller, 404 if the target is not a member."""
    team = await get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    if new_owner_id == user_id:
        raise HTTPException(status_code=422, detail="Choose another member")
    target = await _get_member_or_404(session, team_id=team_id, member_id=new_owner_id)
    current = await _get_member_or_404(session, team_id=team_id, member_id=user_id)
    await repository.swap_owner(session, current_owner=current, new_owner=target)
    return team, TeamRole.MEMBER.value
