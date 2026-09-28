from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot, SavedLineup
from lineup.players import repository as player_repo
from lineup.saved_lineups import repository
from lineup.saved_lineups.schemas import (
    SavedLineupCreate,
    SavedLineupPlayerCreate,
    SavedLineupPlayerResponse,
    SavedLineupResponse,
)
from lineup.teams import repository as team_repo


async def _resolve_team_name(
    session: AsyncSession,
    source_id: uuid.UUID | None,
    explicit_name: str | None,
    not_found_detail: str,
) -> str:
    if source_id is None:
        # Guaranteed non-None by SavedLineupCreate.require_team_identity
        return explicit_name  # type: ignore[return-value]
    team = await team_repo.get_team_by_id(session, team_id=source_id)
    if team is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return explicit_name or team.name


async def _build_player_snapshot(
    session: AsyncSession,
    entry: SavedLineupPlayerCreate,
) -> LineupPlayerSnapshot:
    name = entry.name
    nssz_number = entry.nssz_number
    if entry.source_player_id is not None:
        player = await player_repo.get_player(
            session, player_id=entry.source_player_id, user_id=None
        )
        if player is None:
            raise HTTPException(
                status_code=404,
                detail=f"Player {entry.source_player_id} not found",
            )
        name = name or player.name
        nssz_number = nssz_number or player.nssz_number
    return LineupPlayerSnapshot(
        id=uuid.uuid4(),
        cap_number=entry.cap_number,
        name=name,  # type: ignore[arg-type]
        nssz_number=nssz_number,  # type: ignore[arg-type]
        source_player_id=entry.source_player_id,
    )


def _build_response(lineup: SavedLineup) -> SavedLineupResponse:
    return SavedLineupResponse(
        id=lineup.id,
        team_name=lineup.team_name,
        opponent_name=lineup.opponent_name,
        match_name=lineup.match_name,
        division=lineup.division,
        cap=lineup.cap,
        date=lineup.date,
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
    )


async def create_saved_lineup(
    session: AsyncSession,
    data: SavedLineupCreate,
    user_id: uuid.UUID | None,
) -> SavedLineupResponse:
    team_name = await _resolve_team_name(
        session, data.source_team_id, data.team_name, "Team not found"
    )
    opponent_name = await _resolve_team_name(
        session, data.source_opponent_id, data.opponent_name, "Opponent team not found"
    )
    match_name = data.match_name or f"{team_name} - {opponent_name}"

    player_snapshots = [
        await _build_player_snapshot(session, entry) for entry in data.players
    ]

    lineup = await repository.create_saved_lineup(
        session,
        team_name=team_name,
        opponent_name=opponent_name,
        match_name=match_name,
        division=data.division,
        cap=data.cap,
        date=data.date,
        coach=data.coach,
        doctor=data.doctor,
        assistant_coach=data.assistant_coach,
        team_leader=data.team_leader,
        ball_thrower=data.ball_thrower,
        user_id=user_id,
        source_team_id=data.source_team_id,
        source_opponent_id=data.source_opponent_id,
        player_snapshots=player_snapshots,
    )
    return _build_response(lineup)


async def get_saved_lineup_or_404(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> SavedLineupResponse:
    lineup = await repository.get_saved_lineup(
        session, lineup_id=lineup_id, user_id=user_id
    )
    if lineup is None:
        raise HTTPException(status_code=404, detail="Saved lineup not found")
    return _build_response(lineup)


async def list_saved_lineups(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    source_team_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[SavedLineupResponse], int]:
    lineups, total = await repository.list_saved_lineups(
        session,
        user_id=user_id,
        source_team_id=source_team_id,
        limit=limit,
        offset=offset,
    )
    return [_build_response(lineup) for lineup in lineups], total


async def delete_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> None:
    lineup = await repository.get_saved_lineup(
        session, lineup_id=lineup_id, user_id=user_id
    )
    if lineup is None:
        raise HTTPException(status_code=404, detail="Saved lineup not found")
    await repository.delete_saved_lineup(session, lineup=lineup)
