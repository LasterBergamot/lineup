"""ORM tables: teams, their members and invitations, players, saved lineups and their frozen
player snapshots.

A saved lineup is a *snapshot*: it copies team, opponent and player names as plain text, so
deleting a team or player later never changes history. The `source_*_id` columns are nullable
"soft references" (`ON DELETE SET NULL`) that only remember where a snapshot came from.
Relationships are `lazy="selectin"` because async SQLAlchemy cannot lazy-load on attribute
access (it raises `MissingGreenlet`).
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lineup.db.base import Base


def _utcnow() -> datetime:
    # Columns are TIMESTAMP WITHOUT TIME ZONE, so store naive UTC. SQLite silently drops
    # tzinfo, but asyncpg rejects an aware datetime for such a column.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Team(Base):
    """A club's team. Doubles as a roster (its `players`) and, when `is_public`, as an entry
    in the shared opponent pool.

    A team is a *workspace*: whoever has a row in `team_members` may use its roster and saved
    lineups. `created_by` (the Supabase user id of the creator, who is also its first `owner`
    member) is for auditing only and grants nothing; ownership can move (`team_members.role`).
    A team that still has roster players or saved lineups cannot be deleted (both foreign keys
    are `ON DELETE RESTRICT`; the service reports it as 409 before the database ever has to).

    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    # Whether this team is visible to other users in the shared opponent pool
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # RESTRICT (players.team_id): a team with roster players can't be deleted
    players: Mapped[list["Player"]] = relationship(
        "Player", back_populates="team", lazy="selectin"
    )


class TeamRole(str, Enum):
    """What a user may do in a team. Stored as text (not a database enum) so that adding a role
    later, such as `admin`, is a one-line constraint change instead of a type migration."""

    OWNER = "owner"
    MEMBER = "member"


_ROLE_CHECK = "role IN ('owner', 'member')"


class TeamMember(Base):
    """A user's membership of a team: the row that says "this user may see and edit this team".

    `user_id` is a Supabase user id. It is deliberately not a foreign key: `auth.users` lives in
    another schema that SQLite (local and tests) doesn't have. Rows disappear with their team
    (`ON DELETE CASCADE`). The composite primary key means a user can be in a team only once.

    """

    __tablename__ = "team_members"
    __table_args__ = (
        CheckConstraint(_ROLE_CHECK, name="ck_team_members_role"),
        Index("ix_team_members_user_id", "user_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TeamRole.MEMBER.value
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TeamInvitation(Base):
    """A multi-use invite link into a team. Only the SHA-256 hash of the code is stored
    (`invite_code_hash`): the plaintext is shown once, when the link is created, so a database
    leak doesn't hand out working invitations.

    A link works until `expires_at` or until it is revoked (`revoked_at` set), and admits people
    with the bound `role`. `email` is reserved for a later e-mail-bound variant.

    """

    __tablename__ = "team_invitations"
    __table_args__ = (
        CheckConstraint(_ROLE_CHECK, name="ck_team_invitations_role"),
        Index("ix_team_invitations_team_id", "team_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    invite_code_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TeamRole.MEMBER.value
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Player(Base):
    """A roster entry: a person's name and NSSZ (federation registration) number on a team's
    roster. Visible to every member of that team; `created_by` (Supabase user id) is audit-only.

    Deleting a player is always safe: saved lineups hold copies, not references.

    """

    __tablename__ = "players"
    __table_args__ = (Index("ix_players_team_id", "team_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    nssz_number: Mapped[str] = mapped_column(String(50), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    team: Mapped["Team"] = relationship("Team", back_populates="players")


class SavedLineup(Base):
    """A lineup frozen at creation time, ready to be rendered to PDF/DOCX later.

    Every text column is a copy, so rendering never joins against `teams` or `players`.
    `team_id` is the workspace the lineup lives in: every member of that team can see it
    (`ON DELETE RESTRICT`, so a team with saved lineups can't be deleted). `source_team_id` /
    `source_opponent_id` are soft references (set to NULL if the team is deleted) kept for
    reuse and cloning, and have nothing to do with access. `created_by` is audit-only.
    `player_snapshots` always loads ordered by cap number.

    """

    __tablename__ = "saved_lineups"
    __table_args__ = (Index("ix_saved_lineups_team_id", "team_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )

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
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
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
