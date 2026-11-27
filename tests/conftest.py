"""Fixtures."""

from __future__ import annotations

import pytest

from custom_components.zte_ont import api

from .fake_ont import FakeOnt


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def ont(socket_enabled, monkeypatch):
    monkeypatch.setattr(api, "SCHEME", "http")
    fake = FakeOnt()
    await fake.start()
    yield fake
    await fake.stop()
