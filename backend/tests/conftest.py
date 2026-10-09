"""Test isolation: private SQLite DB, no real Gemini key, and the real dataset (read-only)."""
import os
import tempfile

# Must be set before the app is imported.
_tmp = tempfile.mkdtemp(prefix="claimshield-tests-")
os.environ["CLAIMSHIELD_DB"] = os.path.join(_tmp, "test.db")
os.environ["GEMINI_API_KEY"] = ""  # empty (not unset) so python-dotenv will not load the real key

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def queue(client):
    return client.get("/api/v1/siu/queue").json()


class FakeGemini:
    """Stands in for google-genai's client; records the call and returns canned text."""

    def __init__(self, text=None, error=None):
        self.text, self.error, self.calls = text, error, []
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return type("R", (), {"text": self.text})()
