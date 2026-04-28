from pathlib import Path

import pytest

from files_to_agent.storage import (
    StagingStorage,
    UploadFolderExists,
)


def test_create_folder(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    assert (tmp_path / "abc12345").is_dir()


def test_create_folder_rejects_collision(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    with pytest.raises(UploadFolderExists):
        s.create_folder("abc12345")


def test_save_file_and_size(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    payload = b"hello world"
    saved = s.save_file("abc12345", "greeting.txt", payload)
    assert saved.read_bytes() == payload
    assert s.folder_size("abc12345") == len(payload)
    assert s.file_count("abc12345") == 1


def test_save_file_dedupes_filename_with_suffix(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    s.save_file("abc12345", "x.txt", b"a")
    saved2 = s.save_file("abc12345", "x.txt", b"bb")
    assert saved2.name == "x (1).txt"
    assert s.file_count("abc12345") == 2


def test_delete_folder(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    s.save_file("abc12345", "f.bin", b"x")
    s.delete_folder("abc12345")
    assert not (tmp_path / "abc12345").exists()


def test_list_files(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("abc12345")
    s.save_file("abc12345", "a.txt", b"1")
    s.save_file("abc12345", "b.txt", b"22")
    files = s.list_files("abc12345")
    assert sorted(f.name for f in files) == ["a.txt", "b.txt"]


def test_total_disk_used(tmp_path: Path) -> None:
    s = StagingStorage(tmp_path)
    s.create_folder("a")
    s.save_file("a", "x", b"abcd")
    s.create_folder("b")
    s.save_file("b", "y", b"ef")
    assert s.total_disk_used() == 6
