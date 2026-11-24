"""HTTP endpoints under `/teams/{team_id}/staff`: the team's coach, assistant coach, team leader
and ball thrower entries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.auth.dependencies import get_current_user_id
from lineup.db.engine import get_session
from lineup.staff import service
from lineup.staff.schemas import StaffResponse, StaffWrite

router = APIRouter(prefix="/teams/{team_id}/staff", tags=["staff"])

NOT_FOUND_RESPONSE = {
    "description": (
        "The team does not exist or you are not a member of it, or the `source_player_id` is "
        "not a player of this team. The two cases look the same."
    )
}


@router.get("", response_model=list[StaffResponse], responses={404: NOT_FOUND_RESPONSE})
async def list_staff(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[StaffResponse]:
    """List the team's staff entries (all roles, a plain list in creation order). A role can
    have several entries; at most one per role has `is_default: true`. 404 if the team is
    unknown or you are not a member."""
    items = await service.list_staff(session, team_id=team_id, user_id=user_id)
    return [StaffResponse.model_validate(item) for item in items]


@router.post(
    "",
    response_model=StaffResponse,
    status_code=201,
    responses={404: NOT_FOUND_RESPONSE},
)
async def create_staff(
    team_id: uuid.UUID,
    body: StaffWrite,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> StaffResponse:
    """Add a staff entry, typed in or picked from the roster (`source_player_id`, with the
    player's name copied into `name`). Any member may. With `is_default: true` it becomes the
    default for its role and the previous default of that role is cleared in the same
    transaction. 404 if the team is not yours or `source_player_id` is not on this team's roster."""
    staff = await service.create_staff(
        session, team_id=team_id, body=body, user_id=user_id
    )
    return StaffResponse.model_validate(staff)


@router.put(
    "/{staff_id}",
    response_model=StaffResponse,
    responses={404: NOT_FOUND_RESPONSE},
)
async def update_staff(
    team_id: uuid.UUID,
    staff_id: uuid.UUID,
    body: StaffWrite,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> StaffResponse:
    """Replace every field of a staff entry (role, name, source player, default flag). Setting
    `is_default: true` clears the other default of the resulting role atomically. 404 if the
    team, the staff entry or the `source_player_id` is not reachable."""
    staff = await service.update_staff(
        session, team_id=team_id, staff_id=staff_id, body=body, user_id=user_id
    )
    return StaffResponse.model_validate(staff)


@router.delete("/{staff_id}", status_code=204, responses={404: NOT_FOUND_RESPONSE})
async def delete_staff(
    team_id: uuid.UUID,
    staff_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a staff entry (204). If it was its role's default, the role has no default
    afterwards. 404 if the team or the entry is not reachable."""
    await service.delete_staff(
        session, team_id=team_id, staff_id=staff_id, user_id=user_id
    )
