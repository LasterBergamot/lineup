"""HTTP endpoints for invitation links.

Two routers: `team_router` (`/teams/{team_id}/invitations`, owners create, list and revoke links)
and `router` (`/invitations/{code}`, the person holding a link previews and accepts it).
`GET /invitations/{code}` is the one public route that takes a code, so it is rate limited per
IP, and the code is a secret path segment: the container runs uvicorn with its access log off so
it never reaches the logs.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.auth.dependencies import get_current_display_name, get_current_user_id
from lineup.db.engine import get_session
from lineup.invitations import service
from lineup.invitations.schemas import (
    InvitationCreate,
    InvitationCreated,
    InvitationPreview,
    InvitationResponse,
)
from lineup.security.rate_limit import (
    RATE_LIMIT_RESPONSES,
    invite_ip_limit,
    invite_user_limit,
)
from lineup.teams.schemas import TeamResponse

team_router = APIRouter(prefix="/teams/{team_id}/invitations", tags=["invitations"])
router = APIRouter(prefix="/invitations", tags=["invitations"])

CodePath = Annotated[
    str, Path(max_length=200, description="The code from the invite link.")
]


@team_router.post(
    "",
    response_model=InvitationCreated,
    status_code=201,
    dependencies=[Depends(invite_user_limit)],
    responses=RATE_LIMIT_RESPONSES,
)
async def create_invitation(
    team_id: uuid.UUID,
    body: InvitationCreate | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
    display_name: str | None = Depends(get_current_display_name),
) -> InvitationCreated:
    """Create an invite link for the team (owners only: 403 for other members, 404 for
    non-members). The body is optional; `expires_in_hours` is 2, 24 (default) or 72. The `code`
    and `url` in the response are shown only once. Anyone who opens the link while signed in
    joins as a member until it expires or is revoked."""
    return await service.create_invitation(
        session,
        team_id=team_id,
        user_id=user_id,
        display_name=display_name,
        expires_in_hours=(body or InvitationCreate()).expires_in_hours,
    )


@team_router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[InvitationResponse]:
    """The team's invite links that still work, newest first, without their codes (owners only:
    403 for other members, 404 for non-members)."""
    invitations = await service.list_invitations(
        session, team_id=team_id, user_id=user_id
    )
    return [InvitationResponse.from_invitation(i) for i in invitations]


@team_router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    team_id: uuid.UUID,
    invitation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Revoke an invite link so it stops working (owners only: 403 for other members, 404 for
    non-members or an unknown invitation). People who already joined stay in the team."""
    await service.revoke_invitation(
        session, team_id=team_id, invitation_id=invitation_id, user_id=user_id
    )


@router.get(
    "/{code}",
    response_model=InvitationPreview,
    dependencies=[Depends(invite_ip_limit)],
    responses=RATE_LIMIT_RESPONSES,
)
async def preview_invitation(
    code: CodePath,
    session: AsyncSession = Depends(get_session),
) -> InvitationPreview:
    """Public: what a link is for, so the join page can ask "Join <team>?" before sign-in.
    Returns the team name, the inviter's display name (if known) and the expiry, nothing else.
    404 for an unknown code, 410 when the link expired or was revoked."""
    return await service.preview_invitation(session, code=code)


@router.post(
    "/{code}/accept",
    response_model=TeamResponse,
    dependencies=[Depends(invite_ip_limit), Depends(invite_user_limit)],
    responses=RATE_LIMIT_RESPONSES,
)
async def accept_invitation(
    code: CodePath,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> TeamResponse:
    """Join the team behind the link (sign-in required). Returns the team with your role.
    Safe to repeat: if you are already a member nothing changes (and an owner stays an owner).
    404 for an unknown code, 410 when the link expired or was revoked."""
    team, role = await service.accept_invitation(session, code=code, user_id=user_id)
    return TeamResponse.from_team(team, role)
