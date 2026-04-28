import shutil
from pathlib import Path


class UploadFolderExists(Exception):
    pass


class StagingStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, upload_id: str) -> Path:
        return self.root / upload_id

    def create_folder(self, upload_id: str) -> Path:
        target = self.folder(upload_id)
        if target.exists():
            raise UploadFolderExists(upload_id)
        target.mkdir(parents=True)
        return target

    def save_file(self, upload_id: str, filename: str, payload: bytes) -> Path:
        target_dir = self.folder(upload_id)
        target = target_dir / filename
        if target.exists():
            stem, suffix = target.stem, target.suffix
            i = 1
            while True:
                candidate = target_dir / f"{stem} ({i}){suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                i += 1
        target.write_bytes(payload)
        return target

    def list_files(self, upload_id: str) -> list[Path]:
        d = self.folder(upload_id)
        if not d.exists():
            return []
        return [p for p in d.iterdir() if p.is_file()]

    def folder_size(self, upload_id: str) -> int:
        return sum(p.stat().st_size for p in self.list_files(upload_id))

    def file_count(self, upload_id: str) -> int:
        return len(self.list_files(upload_id))

    def delete_folder(self, upload_id: str) -> None:
        d = self.folder(upload_id)
        if d.exists():
            shutil.rmtree(d)

    def total_disk_used(self) -> int:
        total = 0
        for sub in self.root.iterdir():
            if sub.is_dir():
                total += sum(p.stat().st_size for p in sub.rglob("*") if p.is_file())
        return total
