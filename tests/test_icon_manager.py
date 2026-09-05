"""IconManager path resolution: source runs vs PyInstaller bundles."""

import os
import sys

from utils.icon_manager import IconManager, resource_path


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
    manager = IconManager()
    assert manager.path.endswith(os.path.join("assets", "icons"))
