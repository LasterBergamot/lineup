from uuid import UUID


async def get_current_user_id() -> UUID | None:
    """
    Pre-Auth: always returns None — no user-scoped filtering is applied.
    Post-Auth (Supabase): replace this body to extract the `sub` claim from
    the incoming Bearer JWT. All routers and repositories remain unchanged.
    """
    return None
