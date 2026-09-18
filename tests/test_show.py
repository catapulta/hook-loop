import show


def test_invalidate_stl_removes_conventional_export(monkeypatch, tmp_path):
    monkeypatch.setattr(show, "ROOT", tmp_path)
    export = tmp_path / "out" / "widget.stl"
    export.parent.mkdir()
    export.write_bytes(b"stale")

    assert show.invalidate_stl("widget") == export
    assert not export.exists()


def test_invalidate_stl_accepts_missing_export(monkeypatch, tmp_path):
    monkeypatch.setattr(show, "ROOT", tmp_path)

    assert show.invalidate_stl("widget") is None
