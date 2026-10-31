"""Team members and ownership (#51): list, remove / leave, transfer.

A second person is simulated by flipping `current_user.id`; membership rows are added directly
(`join_team`), because joining through an invitation link is covered in test_invitations.py.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import CurrentUser
from tests.helpers import create_player, ensure_team, join_team


async def _team_with_member(
    client: AsyncClient, db_session: AsyncSession, current_user: CurrentUser
) -> tuple[dict, uuid.UUID, uuid.UUID]:
    """A team, its owner's id and the id of a plain member. Signed in as the owner."""
    team = await ensure_team(client)
    owner = current_user.id
    member = uuid.uuid4()
    await join_team(db_session, team["id"], member)
    return team, owner, member


class TestListMembers:
    async def test_lists_ids_roles_and_marks_you(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        response = await async_client.get(f"/teams/{team['id']}/members")
        assert response.status_code == 200
        rows = response.json()
        assert [(r["user_id"], r["role"], r["is_you"]) for r in rows] == [
            (str(owner), "owner", True),
            (str(member), "member", False),
        ]
        assert set(rows[0]) == {"user_id", "role", "joined_at", "is_you"}

    async def test_a_plain_member_may_list_too(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, _owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        current_user.id = member
        rows = (await async_client.get(f"/teams/{team['id']}/members")).json()
        assert [r["is_you"] for r in rows] == [False, True]

    async def test_strangers_get_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        current_user.id = uuid.uuid4()
        assert (
            await async_client.get(f"/teams/{team['id']}/members")
        ).status_code == 404
        unknown = await async_client.get(f"/teams/{uuid.uuid4()}/members")
        assert unknown.status_code == 404


class TestRemoveMember:
    async def test_owner_removes_a_member_who_then_loses_access(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, _owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        response = await async_client.delete(f"/teams/{team['id']}/members/{member}")
        assert response.status_code == 204
        current_user.id = member
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 404

    async def test_the_roster_stays_with_the_team(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        current_user.id = member
        player = await create_player(async_client, team_id=team["id"])
        current_user.id = owner
        await async_client.delete(f"/teams/{team['id']}/members/{member}")
        assert (await async_client.get(f"/players/{player['id']}")).status_code == 200

    async def test_a_member_can_leave(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, _owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        current_user.id = member
        response = await async_client.delete(f"/teams/{team['id']}/members/{member}")
        assert response.status_code == 204
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 404

    async def test_a_member_cannot_remove_somebody_else(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        current_user.id = member
        response = await async_client.delete(f"/teams/{team['id']}/members/{owner}")
        assert response.status_code == 403

    async def test_the_last_owner_cannot_leave(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        response = await async_client.delete(
            f"/teams/{team['id']}/members/{current_user.id}"
        )
        assert response.status_code == 409
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200

    async def test_an_owner_can_leave_when_another_owner_remains(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        second = uuid.uuid4()
        await join_team(db_session, team["id"], second, role="owner")
        response = await async_client.delete(
            f"/teams/{team['id']}/members/{current_user.id}"
        )
        assert response.status_code == 204

    async def test_unknown_member_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        response = await async_client.delete(
            f"/teams/{team['id']}/members/{uuid.uuid4()}"
        )
        assert response.status_code == 404

    async def test_strangers_get_404_and_cannot_touch_members_of_other_teams(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, _owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        current_user.id = uuid.uuid4()
        response = await async_client.delete(f"/teams/{team['id']}/members/{member}")
        assert response.status_code == 404
        # ... and a team of the stranger's own does not give them reach into this one
        mine = await ensure_team(async_client, "Mine")
        wrong_team = await async_client.delete(f"/teams/{mine['id']}/members/{member}")
        assert wrong_team.status_code == 404
        current_user.id = member
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200


class TestTransferOwnership:
    async def test_hands_the_team_over(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        response = await async_client.post(
            f"/teams/{team['id']}/transfer-ownership", json={"user_id": str(member)}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "member"  # the caller's new role
        roles = {
            r["user_id"]: r["role"]
            for r in (await async_client.get(f"/teams/{team['id']}/members")).json()
        }
        assert roles == {str(owner): "member", str(member): "owner"}

    async def test_the_new_owner_gains_and_the_old_one_loses_owner_rights(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        await async_client.post(
            f"/teams/{team['id']}/transfer-ownership", json={"user_id": str(member)}
        )
        invite = f"/teams/{team['id']}/invitations"
        assert (await async_client.post(invite)).status_code == 403
        current_user.id = member
        assert (await async_client.post(invite)).status_code == 201
        # the former owner can now leave
        current_user.id = owner
        left = await async_client.delete(f"/teams/{team['id']}/members/{owner}")
        assert left.status_code == 204

    async def test_target_must_be_a_member(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/transfer-ownership",
            json={"user_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404

    async def test_cannot_hand_over_to_yourself(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/transfer-ownership",
            json={"user_id": str(current_user.id)},
        )
        assert response.status_code == 422

    async def test_members_cannot_and_strangers_get_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team, _owner, member = await _team_with_member(
            async_client, db_session, current_user
        )
        url = f"/teams/{team['id']}/transfer-ownership"
        current_user.id = member
        assert (
            await async_client.post(url, json={"user_id": str(member)})
        ).status_code == 403
        current_user.id = uuid.uuid4()
        assert (
            await async_client.post(url, json={"user_id": str(member)})
        ).status_code == 404

    async def test_needs_a_valid_body(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/transfer-ownership", json={"user_id": "nope"}
        )
        assert response.status_code == 422
