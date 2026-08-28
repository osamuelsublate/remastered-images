"""Shared pytest fixtures.

Isolates each test from the real ``backend/data`` directory by overriding
the ``api/deps`` storage providers (instead of touching environment
variables, which would race the composition root's module-level caching)
and exposes a ready-to-use FastAPI ``TestClient``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.repositories.file_carousel_repository import FileCarouselRepository
from app.adapters.storage.local_media_storage import LocalMediaStorage
from app.api import deps
from app.main import app


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path):
    carousels_dir = tmp_path / "carousels"
    carousels_dir.mkdir()
    app.dependency_overrides[deps.get_carousel_repository] = lambda: FileCarouselRepository(
        carousels_dir
    )
    app.dependency_overrides[deps.get_media_storage] = lambda: LocalMediaStorage(carousels_dir)
    yield
    app.dependency_overrides.pop(deps.get_carousel_repository, None)
    app.dependency_overrides.pop(deps.get_media_storage, None)


@pytest.fixture
def client():
    return TestClient(app)
