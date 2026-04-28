from fastapi import Header, HTTPException

from files_to_agent.config import Settings


def make_auth_dependency(settings: Settings):  # type: ignore[return]
    async def _dep(authorization: str | None = Header(default=None)) -> None:
        if settings.resolver_auth == "none":
            return
        expected = f"Bearer {settings.resolver_api_key}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="unauthorized")

    return _dep
