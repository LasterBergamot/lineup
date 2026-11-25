"""Business rules for saved lineups: turning a create or edit request into a snapshot.

Team, opponent and each player come either from the live roster (`source_*_id`, whose current
name/NSSZ is copied in) or from free text, exactly one of the two (enforced by the schemas).
Nothing here is a live reference afterwards. Create and edit share the resolution
(`_resolve_content`), so an edit follows exactly the same lookups, 404s and 422s as a create.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot, SavedLineup
from lineup.players import repository as player_repo
from lineup.saved_lineups import repository
from lineup.saved_lineups.schemas import (
    SavedLineupCreate,
    SavedLineupFields,
    SavedLineupPlayerCreate,
    SavedLineupPlayerResponse,
    SavedLineupResponse,
    SavedLineupUpdate,
)
from lineup.teams import repository as team_repo

STALE_EDIT_DETAIL = (
    "This saved lineup was changed since you loaded it. Reload it and edit it again."
)


async def _resolve_team_name(
    session: AsyncSession,
    source_id: uuid.UUID | None,
    explicit_name: str | None,
    not_found_detail: str,
    user_id: uuid.UUID,
    allow_listed: bool,
) -> str:
    """Name of the referenced team, or `explicit_name` for free text.

    The referenced team must be one the caller belongs to; with `allow_listed` (opponents) a team
    listed in the opponent directory also qualifies. Anything else is 404, the same as a missing id, so
    the API never confirms that someone else's team exists.
    """
    if source_id is None:
        # Exactly one of the two is set: SavedLineupCreate.require_team_identity
        return explicit_name  # type: ignore[return-value]
    if allow_listed:
        team = await team_repo.get_team_visible(
            session, team_id=source_id, user_id=user_id
        )
    else:
        found = await team_repo.get_team(session, team_id=source_id, user_id=user_id)
        team = None if found is None else found[0]
    if team is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return team.name


async def _build_player_snapshot(
    session: AsyncSession,
    entry: SavedLineupPlayerCreate,
    user_id: uuid.UUID,
) -> LineupPlayerSnapshot:
    # Exactly one of source_player_id / free text is set: require_identity
    name = entry.name
    nssz_number = entry.nssz_number
    if entry.source_player_id is not None:
        player = await player_repo.get_player(
            session, player_id=entry.source_player_id, user_id=user_id
        )
        if player is None:
            raise HTTPException(
                status_code=404,
                detail=f"Player {entry.source_player_id} not found",
            )
        name = player.name
        nssz_number = player.nssz_number
    return LineupPlayerSnapshot(
        id=uuid.uuid4(),
        cap_number=entry.cap_number,
        name=name,  # type: ignore[arg-type]
        nssz_number=nssz_number,  # type: ignore[arg-type]
        source_player_id=entry.source_player_id,
    )


def _ensure_unique_nssz(snapshots: list[LineupPlayerSnapshot]) -> None:
    """Checked on the resolved values, because a roster player's NSSZ number is only known
    after the lookup (and could equal a free-text one)."""
    numbers = [s.nssz_number.casefold() for s in snapshots]
    if len(numbers) != len(set(numbers)):
        raise HTTPException(
            status_code=422,
            detail="A player's NSSZ number cannot appear more than once in a lineup",
        )


def _build_response(lineup: SavedLineup) -> SavedLineupResponse:
    return SavedLineupResponse(
        id=lineup.id,
        team_id=lineup.team_id,
        team_name=lineup.team_name,
        opponent_name=lineup.opponent_name,
        match_name=lineup.match_name,
        division=lineup.division,
        cap=lineup.cap,
        date=lineup.date,
        match_date=lineup.match_date,
        match_time=lineup.match_time,
        location=lineup.location,
        coach=lineup.coach,
        doctor=lineup.doctor,
        assistant_coach=lineup.assistant_coach,
        team_leader=lineup.team_leader,
        ball_thrower=lineup.ball_thrower,
        source_team_id=lineup.source_team_id,
        source_opponent_id=lineup.source_opponent_id,
        players=[
            SavedLineupPlayerResponse.model_validate(snapshot)
            for snapshot in lineup.player_snapshots
        ],
        created_at=lineup.created_at,
        updated_at=lineup.updated_at,
    )


async def _resolve_content(
    session: AsyncSession,
    data: SavedLineupFields,
    user_id: uuid.UUID,
) -> tuple[dict, list[LineupPlayerSnapshot]]:
    """The column values and player snapshots for a create or edit request, resolved as the caller.

    Resolves team and opponent names (404 if a source id is unknown or not reachable for the
    caller), defaults the match name to "<team> - <opponent>", builds the player snapshots
    (404 if a source player is unknown) and rejects duplicate NSSZ numbers with 422, checked on
    the resolved values. Returns the editable columns as a dict (every column except the
    workspace, the audit fields and the timestamps) and the snapshots, not yet attached.
    """
    team_name = await _resolve_team_name(
        session, data.source_team_id, data.team_name, "Team not found", user_id, False
    )
    opponent_name = await _resolve_team_name(
        session,
        data.source_opponent_id,
        data.opponent_name,
        "Opponent team not found",
        user_id,
        True,
    )
    player_snapshots = [
        await _build_player_snapshot(session, entry, user_id) for entry in data.players
    ]
    _ensure_unique_nssz(player_snapshots)
    fields = {
        "team_name": team_name,
        "opponent_name": opponent_name,
        "match_name": data.match_name or f"{team_name} - {opponent_name}",
        "division": data.division,
        "cap": data.cap,
        "date": data.date,
        "match_date": data.match_date,
        "match_time": data.match_time,
        "location": data.location,
        "coach": data.coach,
        "doctor": data.doctor,
        "assistant_coach": data.assistant_coach,
        "team_leader": data.team_leader,
        "ball_thrower": data.ball_thrower,
        "source_team_id": data.source_team_id,
        "source_opponent_id": data.source_opponent_id,
    }
    return fields, player_snapshots


async def create_saved_lineup(
    session: AsyncSession,
    data: SavedLineupCreate,
    user_id: uuid.UUID,
) -> SavedLineupResponse:
    """Save a lineup as a snapshot in the workspace of `data.team_id` and return it.

    The caller must belong to that team (404 "Team not found" otherwise). Resolves team and opponent names (404 if a source id is unknown), defaults the match name to
    "<team> - <opponent>", builds the player snapshots (404 if a source player is unknown) and
    rejects duplicate NSSZ numbers with 422, checked on the resolved values.
    """
    workspace = await team_repo.get_team(session, team_id=data.team_id, user_id=user_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Team not found")
    fields, player_snapshots = await _resolve_content(session, data, user_id)
    lineup = await repository.create_saved_lineup(
        session,
        **fields,
        created_by=user_id,
        team_id=data.team_id,
        player_snapshots=player_snapshots,
    )
    return _build_response(lineup)


async def update_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    data: SavedLineupUpdate,
    user_id: uuid.UUID,
) -> SavedLineupResponse:
    """Edit a saved lineup in place (same id, same team) and return the new version.

    Any member of the lineup's team may edit it, as with delete; a lineup of a team the caller
    is not in is 404 "Saved lineup not found". The content is resolved exactly like a create
    (`_resolve_content`: the same 404s and 422s), then every column and all player snapshots
    are replaced in one transaction. Raises 409 when `data.expected_updated_at` is not the
    lineup's current `updated_at`, which means someone saved it in the meantime; nothing is
    changed then. The 409 body is a fixed text that names no one and echoes no stored value.
    """
    lineup = await repository.get_saved_lineup(
        session, lineup_id=lineup_id, user_id=user_id
    )
    if lineup is None:
        raise HTTPException(status_code=404, detail="Saved lineup not found")
    if lineup.updated_at != data.expected_updated_at:
        raise HTTPException(status_code=409, detail=STALE_EDIT_DETAIL)
    fields, player_snapshots = await _resolve_content(session, data, user_id)
    updated = await repository.update_saved_lineup(
        session,
        lineup_id=lineup_id,
        expected_updated_at=data.expected_updated_at,
        fields=fields,
        player_snapshots=player_snapshots,
    )
    if updated is None:  # another edit committed between the check above and the update
        raise HTTPException(status_code=409, detail=STALE_EDIT_DETAIL)
    return _build_response(updated)


async def get_saved_lineup_or_404(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SavedLineupResponse:
    """Return the lineup or raise 404 "Saved lineup not found"."""
    lineup = await repository.get_saved_lineup(
        session, lineup_id=lineup_id, user_id=user_id
    )
    if lineup is None:
        raise HTTPException(status_code=404, detail="Saved lineup not found")
    return _build_response(lineup)


async def list_saved_lineups(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_team_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
    limit: int,
    offset: int,
    opponent: str | None = None,
    location: str | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
) -> tuple[list[SavedLineupResponse], int]:
    """One page of the lineups of the caller's teams (optionally for one workspace or one
    source team, and narrowed by the search filters, see `repository.list_saved_lineups`) and
    the total count. Search terms are trimmed and a blank one means "no filter"; they are never
    logged.
    """
    lineups, total = await repository.list_saved_lineups(
        session,
        user_id=user_id,
        source_team_id=source_team_id,
        team_id=team_id,
        opponent=(opponent or "").strip() or None,
        location=(location or "").strip() or None,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [_build_response(lineup) for lineup in lineups], total


async def delete_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a lineup, or raise 404 if it is not found."""
    lineup = await repository.get_saved_lineup(
        session, lineup_id=lineup_id, user_id=user_id
    )
    if lineup is None:
        raise HTTPException(status_code=404, detail="Saved lineup not found")
    await repository.delete_saved_lineup(session, lineup=lineup)
