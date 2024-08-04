import pytest


@pytest.fixture(scope="module")
def app():
    from app.main import create_app

    app = create_app()

    app.config.update({"TESTING": True})

    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()
