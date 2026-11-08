"""Unit tests for main.py (composition is patched out)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main as main_module


@pytest.fixture()
def patched(monkeypatch):
    logger = MagicMock()
    view = MagicMock()
    controller = MagicMock()
    container = SimpleNamespace(
        library=MagicMock(name="library"),
        player=MagicMock(name="player"),
        playlists=MagicMock(name="playlists"),
        controller=None,
    )
    monkeypatch.setattr(main_module, "logger", logger)
    monkeypatch.setattr(main_module, "init_db", MagicMock())
    monkeypatch.setattr(main_module, "View", MagicMock(return_value=view))
    monkeypatch.setattr(main_module, "build_container", MagicMock(return_value=container))
    monkeypatch.setattr(main_module, "MainController", MagicMock(return_value=controller))
    return SimpleNamespace(
        logger=logger,
        view=view,
        controller=controller,
        container=container,
        init_db=main_module.init_db,
        View=main_module.View,
        build_container=main_module.build_container,
        MainController=main_module.MainController,
    )


def test_main_wires_container_view_and_controller(patched):
    main_module.main()

    patched.init_db.assert_called_once()
    patched.View.assert_called_once()
    patched.build_container.assert_called_once_with(view=None)
    patched.MainController.assert_called_once_with(
        view=patched.view,
        library=patched.container.library,
        player=patched.container.player,
        playlists=patched.container.playlists,
    )
    assert patched.container.controller is patched.controller
    patched.view.set_controller.assert_called_once_with(patched.controller)
    patched.controller.bind.assert_called_once()
    patched.view.after.assert_called_once_with(100, patched.controller.refresh_library_view)
    patched.controller.run.assert_called_once()
    patched.logger.remove.assert_called_once()
    assert patched.logger.add.call_count == 2


def test_main_reraises_and_logs_crash(patched):
    patched.View.side_effect = RuntimeError("no display")

    with pytest.raises(RuntimeError, match="no display"):
        main_module.main()

    patched.logger.exception.assert_called_once_with("App crashed")
    patched.controller.run.assert_not_called()
