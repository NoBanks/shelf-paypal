"""Gemini key pool: env list, numbered env vars, keystore file, single key."""
import json

from shelf import run_local


def test_pool_prefers_gemini_keys_list(monkeypatch):
    monkeypatch.setenv("GEMINI_KEYS", "a, b ,c")
    assert run_local._pool() == ["a", "b", "c"]


def test_pool_collects_numbered_env_vars_in_order(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_KEYS", raising=False)
    monkeypatch.setattr(run_local, "KEYSTORE", str(tmp_path / "missing.json"))
    for k in list(dict(__import__("os").environ)):
        if k.startswith("GEMINI_API_KEY") or k == "GOOGLE_API_KEY":
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_10", "k10")
    monkeypatch.setenv("GEMINI_API_KEY_2", "k2")
    monkeypatch.setenv("GEMINI_API_KEY", "k0")
    assert run_local._pool() == ["k0", "k2", "k10"]


def test_pool_falls_back_to_keystore_then_single_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_KEYS", raising=False)
    for k in list(dict(__import__("os").environ)):
        if k.startswith("GEMINI_API_KEY") or k == "GOOGLE_API_KEY":
            monkeypatch.delenv(k, raising=False)
    ks = tmp_path / "keys.json"
    ks.write_text(json.dumps({"keys": ["f1", "f2"]}))
    monkeypatch.setattr(run_local, "KEYSTORE", str(ks))
    assert run_local._pool() == ["f1", "f2"]
    monkeypatch.setattr(run_local, "KEYSTORE", str(tmp_path / "nope.json"))
    monkeypatch.setenv("GOOGLE_API_KEY", "g")
    assert run_local._pool() == ["g"]


def test_load_key_sets_google_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_KEYS", "x,y")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    run_local.load_key(1)
    assert __import__("os").environ["GOOGLE_API_KEY"] == "y"
