from importlib import reload
from pathlib import Path

import pytest


def test_loads_database_url_from_env_with_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")

    import markr.config as config

    reload(config)
    settings = config.Settings()

    assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@h/d"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.WRITE_POOL_SIZE == 10


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import markr.config as config

    reload(config)
    with pytest.raises(Exception):
        config.Settings()
