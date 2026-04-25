from __future__ import annotations

from pathlib import Path

import pytest

from helpers import files


def test_resolve_path_in_root_allows_paths_within_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "a" / "b.txt"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("ok", encoding="utf-8")

    resolved = files.resolve_path_in_root("a/b.txt", str(root), must_exist=True)
    assert resolved == str(nested.resolve())


def test_resolve_path_in_root_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside.txt"
    root.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid file path"):
        files.resolve_path_in_root("../outside.txt", str(root), must_exist=False)


def test_resolve_path_in_root_rejects_missing_when_required(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="Path does not exist"):
        files.resolve_path_in_root("missing.txt", str(root), must_exist=True)


def test_resolve_path_in_root_maps_a0_dev_paths(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    upload = root / "usr" / "uploads" / "file.txt"
    upload.parent.mkdir(parents=True)
    upload.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(files, "get_base_dir", lambda: str(root))
    monkeypatch.setattr("helpers.runtime.is_dockerized", lambda: False)

    resolved = files.resolve_path_in_root(
        "/a0/usr/uploads/file.txt", str(root), must_exist=True
    )
    assert resolved == str(upload.resolve())
