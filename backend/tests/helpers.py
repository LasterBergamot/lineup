"""Small helpers shared by the API tests.

Players and saved lineups must live in a team the caller belongs to, so most tests need "a team"
first. `ensure_team` gives them one without each test repeating the setup.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import TeamMember

DEFAULT_TEAM = "SZVTK"


async def ensure_team(
    client: AsyncClient, name: str = DEFAULT_TEAM, is_public: bool = True
) -> dict:
    """Return the caller's team called `name`, creating it on first use."""
    listing = await client.get("/teams?limit=200")
    for team in listing.json()["items"]:
        if team["name"] == name:
            return team
    response = await client.post("/teams", json={"name": name, "is_public": is_public})
    assert response.status_code == 201
    return response.json()


async def create_player(
    client: AsyncClient,
    name: str = "Török András",
    nssz_number: str = "MVLSZ001",
    team_id: str | None = None,
) -> dict:
    """Create a player on `team_id`, or on the caller's default team when omitted."""
    if team_id is None:
        team_id = (await ensure_team(client))["id"]
    response = await client.post(
        "/players", json={"name": name, "nssz_number": nssz_number, "team_id": team_id}
    )
    assert response.status_code == 201
    return response.json()


async def join_team(
    db_session: AsyncSession, team_id: str, user_id: uuid.UUID, role: str = "member"
) -> None:
    """Make `user_id` a member of the team directly in the database (no invitation involved)."""
    db_session.add(TeamMember(team_id=uuid.UUID(team_id), user_id=user_id, role=role))
    await db_session.commit()
