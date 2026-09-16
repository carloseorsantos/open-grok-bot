from src.config import Settings


def test_settings_initialization(tmp_path):
    settings = Settings(
        DATABASE_PATH=tmp_path / "test.db",
        WORKSPACE_DIR=tmp_path / "workspace",
        SCREENSHOTS_DIR=tmp_path / "screenshots",
        TELEGRAM_ALLOWED_USERS="12345, 67890"
    )
    assert settings.DATABASE_PATH.parent.exists()
    assert settings.WORKSPACE_DIR.exists()
    assert settings.SCREENSHOTS_DIR.exists()
    assert settings.allowed_telegram_ids == [12345, 67890]
