from datetime import UTC, datetime
from pathlib import Path

import pytest

from files_to_agent.core import Core
from files_to_agent.db import connect, init_schema
from files_to_agent.storage import StagingStorage


@pytest.fixture
def core(tmp_path: Path) -> Core:
    conn = connect(tmp_path / "t.db")
    init_schema(conn)
    return Core(
        conn=conn,
        storage=StagingStorage(tmp_path / "staging"),
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_get_chat_lang_returns_none_when_unset(core: Core) -> None:
    assert core.get_chat_lang(123) is None


def test_set_then_get_chat_lang(core: Core) -> None:
    core.set_chat_lang(123, "en")
    assert core.get_chat_lang(123) == "en"


def test_set_chat_lang_overwrites(core: Core) -> None:
    core.set_chat_lang(123, "it")
    core.set_chat_lang(123, "en")
    assert core.get_chat_lang(123) == "en"


def test_set_chat_lang_rejects_unsupported(core: Core) -> None:
    with pytest.raises(ValueError):
        core.set_chat_lang(123, "fr")


def test_lang_isolated_per_chat(core: Core) -> None:
    core.set_chat_lang(1, "it")
    core.set_chat_lang(2, "en")
    assert core.get_chat_lang(1) == "it"
    assert core.get_chat_lang(2) == "en"
