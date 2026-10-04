import app.db as db


def test_engine_and_session_factory_configured() -> None:
    assert db.engine is not None
    assert db.async_session_factory is not None