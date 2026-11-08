"""Unit tests for views/icon_manager.py."""

from __future__ import annotations

import os
import sys

import pytest

from views import icon_manager
from views.icon_manager import IconManager, icons, resource_path


def test_resource_path_source_run_uses_cwd(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert resource_path(os.path.join("assets", "icons")) == os.path.abspath(
        os.path.join(".", "assets", "icons")
    )


def test_resource_path_bundle_run_uses_meipass(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path(os.path.join("assets", "icons")) == os.path.join(
        str(tmp_path), "assets", "icons"
    )


def test_default_icon_path_resolves_to_assets_icons():
    assert IconManager().path.endswith(os.path.join("assets", "icons"))
    assert icons.path.endswith(os.path.join("assets", "icons"))


def test_custom_icon_path():
    assert IconManager("/tmp/icons").path == "/tmp/icons"


def test_load_uses_same_image_for_light_and_dark(monkeypatch):
    opened = []
    sentinel = object()

    def fake_open(path):
        opened.append(path)
        return sentinel

    monkeypatch.setattr(icon_manager.Image, "open", fake_open)
    image = IconManager("/icons").load("play", (32, 30))

    assert opened == ["/icons/play.png", "/icons/play.png"]
    assert image.light_image is sentinel
    assert image.dark_image is sentinel
    assert image.size == (32, 30)


def test_load_with_dark_variant(monkeypatch):
    opened = []
    monkeypatch.setattr(icon_manager.Image, "open", lambda path: opened.append(path) or path)
    image = IconManager("/icons").load("logo", (10, 20), with_dark=True)

    assert opened == ["/icons/logo_light.png", "/icons/logo_dark.png"]
    assert image.light_image == "/icons/logo_light.png"
    assert image.dark_image == "/icons/logo_dark.png"
    assert image.size == (10, 20)


def test_load_default_size(monkeypatch):
    monkeypatch.setattr(icon_manager.Image, "open", lambda path: path)
    assert IconManager("/icons").load("x").size == (20, 20)


def test_missing_icon_raises_file_not_found(tmp_path):
    manager = IconManager(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        manager.load("does_not_exist")
