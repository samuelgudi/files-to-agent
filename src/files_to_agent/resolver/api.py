from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from files_to_agent.config import Settings
from files_to_agent.core import Core, InvalidStatusTransition, UploadNotFound
from files_to_agent.resolver.auth import make_auth_dependency


class UseRequest(BaseModel):
    ref: str
    action: str
    details: dict[str, Any] | None = None


class UploadResponse(BaseModel):
    id: str
    name: str | None
    context: str | None
    status: str
    path: str
    files: list[str]
    size_bytes: int
    file_count: int
    created_at: str
    confirmed_at: str | None
    last_used_at: str | None


def build_app(core: Core, settings: Settings) -> FastAPI:
    app = FastAPI(title="FilesToAgent Resolver")
    auth = make_auth_dependency(settings)

    def _to_response(upload_id: str) -> UploadResponse:
        u = core.get_upload(upload_id)
        files = [p.name for p in core.storage.list_files(u.id)]
        return UploadResponse(
            id=u.id,
            name=u.name,
            context=u.context,
            status=u.status.value,
            path=str(core.storage.folder(u.id)),
            files=files,
            size_bytes=u.size_bytes,
            file_count=u.file_count,
            created_at=u.created_at.isoformat(),
            confirmed_at=u.confirmed_at.isoformat() if u.confirmed_at else None,
            last_used_at=u.last_used_at.isoformat() if u.last_used_at else None,
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/resolve", response_model=UploadResponse, dependencies=[Depends(auth)])
    async def resolve(ref: str) -> UploadResponse:
        try:
            u = core.find_by_ref(ref)
        except UploadNotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return _to_response(u.id)

    @app.post("/use", response_model=UploadResponse, dependencies=[Depends(auth)])
    async def use(req: UseRequest) -> UploadResponse:
        try:
            u = core.find_by_ref(req.ref)
        except UploadNotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        try:
            core.mark_used(u.id, action=req.action, details=req.details)
        except InvalidStatusTransition as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return _to_response(u.id)

    return app
