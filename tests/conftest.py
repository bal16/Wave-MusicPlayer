"""Global test bootstrap.

The fakes must be installed before any ``views`` module is imported, so this
runs at conftest import time (pytest loads conftest before test modules).
"""

from __future__ import annotations

import pytest

from tests.support import fake_tk

fake_tk.install()

from tests.support.doubles import make_playlist, make_song  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_fake_toolkit():
    """Keep GUI recorder state isolated between tests."""
    fake_tk.reset()
    from views.widgets import scroll_helper

    scroll_helper._registry.clear()
    scroll_helper._keys_bound = False
    yield
    fake_tk.reset()
    scroll_helper._registry.clear()
    scroll_helper._keys_bound = False


@pytest.fixture()
def song():
    return make_song(1)


@pytest.fixture()
def playlist():
    return make_playlist(1)
