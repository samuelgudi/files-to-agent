from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class UploadStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    USED = "used"


class Upload(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str | None
    chat_id: int
    created_at: datetime
    confirmed_at: datetime | None
    last_used_at: datetime | None
    size_bytes: int
    file_count: int
    status: UploadStatus
    context: str | None = None

    @property
    def is_active_draft(self) -> bool:
        return self.status == UploadStatus.DRAFT

    @property
    def is_used(self) -> bool:
        return self.status == UploadStatus.USED


class UsageLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    upload_id: str
    used_at: datetime
    action: str
    details: dict[str, Any] | None = None
