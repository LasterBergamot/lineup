"""ORM tables: teams, players, saved lineups and their frozen player snapshots.

A saved lineup is a *snapshot*: it copies team, opponent and player names as plain text, so
deleting a team or player later never changes history. The `source_*_id` columns are nullable
"soft references" (`ON DELETE SET NULL`) that only remember where a snapshot came from.
Relationships are `lazy="selectin"` because async SQLAlchemy cannot lazy-load on attribute
access (it raises `MissingGreenlet`).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lineup.db.base import Base


def _utcnow() -> datetime:
    # Columns are TIMESTAMP WITHOUT TIME ZONE, so store naive UTC. SQLite silently drops
    # tzinfo, but asyncpg rejects an aware datetime for such a column.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Team(Base):
    """A club's team. Doubles as a roster (its `players`) and, when `is_public`, as an entry
    in the shared opponent pool.

    `owner_id` is always NULL until real auth exists. A team that still has roster players
    cannot be deleted (`players.team_id` is `ON DELETE RESTRICT`; the service reports it as 409
    before the database ever has to).

    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # owner_id is nullable pre-Auth; becomes NOT NULL when Supabase Auth is wired in
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    # Whether this team is visible to other users in the shared opponent pool
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # RESTRICT (players.team_id): a team with roster players can't be deleted
    players: Mapped[list["Player"]] = relationship(
        "Player", back_populates="team", lazy="selectin"
    )


class Player(Base):
    """A roster entry: a person's name and NSSZ (federation registration) number, optionally
    assigned to a team. `user_id` is NULL until real auth exists.

    Deleting a player is always safe: saved lineups hold copies, not references.

    """

    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    nssz_number: Mapped[str] = mapped_column(String(50), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True
    )
    # user_id nullable pre-Auth
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    team: Mapped["Team | None"] = relationship("Team", back_populates="players")


class SavedLineup(Base):
    """A lineup frozen at creation time, ready to be rendered to PDF/DOCX later.

    Every text column is a copy, so rendering never joins against `teams` or `players`.
    `source_team_id` / `source_opponent_id` are soft references (set to NULL if the team is
    deleted) kept for reuse and cloning. `player_snapshots` always loads ordered by cap number.

    """

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

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
    """One player slot of a saved lineup: the name and NSSZ number as they were when the
    lineup was saved, plus the cap number. `source_player_id` is a soft reference (NULL once
    the roster player is deleted). Deleted together with its lineup (`ON DELETE CASCADE`).

    """

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
