import uuid
from datetime import datetime, timezone

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lineup.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # owner_id is nullable pre-Auth; becomes NOT NULL when Supabase Auth is wired in
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    # Whether this team is visible to other users in the shared opponent pool
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # RESTRICT (players.team_id): a team with roster players can't be deleted
    players: Mapped[list["Player"]] = relationship(
        "Player", back_populates="team", lazy="selectin"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    nssz_number: Mapped[str] = mapped_column(String(50), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True
    )
    # user_id nullable pre-Auth
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    team: Mapped["Team | None"] = relationship("Team", back_populates="players")


class SavedLineup(Base):
    __tablename__ = "saved_lineups"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    # Frozen text snapshot, self-contained: rendering never needs to join
    # against teams/players, and deleting either has zero effect on this row.
    team_name: Mapped[str] = mapped_column(String(120), nullable=False)
    opponent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    match_name: Mapped[str] = mapped_column(String(200), nullable=False)
    division: Mapped[str] = mapped_column(String(100), nullable=False)
    # "Fehér" or "Kék" — validated at the API layer via Pydantic
    cap: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[str] = mapped_column(String(50), nullable=False)
    coach: Mapped[str] = mapped_column(String(200), nullable=False)
    doctor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    assistant_coach: Mapped[str | None] = mapped_column(String(200), nullable=True)
    team_leader: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ball_thrower: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # user_id nullable pre-Auth
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Optional soft references for reuse/cloning; nulled out if the source is
    # deleted so a saved lineup is never blocked on or broken by that deletion.
    source_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    source_opponent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )

    player_snapshots: Mapped[list["LineupPlayerSnapshot"]] = relationship(
        "LineupPlayerSnapshot",
        back_populates="saved_lineup",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LineupPlayerSnapshot.cap_number",
    )


class LineupPlayerSnapshot(Base):
    __tablename__ = "lineup_player_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    saved_lineup_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("saved_lineups.id", ondelete="CASCADE"), nullable=False
    )
    cap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    nssz_number: Mapped[str] = mapped_column(String(50), nullable=False)
    # Soft reference, nulled out (not blocked) when the source player is deleted
    source_player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )

    saved_lineup: Mapped["SavedLineup"] = relationship(
        "SavedLineup", back_populates="player_snapshots"
    )
