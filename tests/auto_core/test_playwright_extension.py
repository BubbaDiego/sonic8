import os
import pytest
from backend.core.auto_core.playwright_helper import PlaywrightHelper
import backend.core.auto_core.playwright_helper as helper

class DummyLog:
    def __init__(self):
        self.warnings = []
    def warning(self, msg, source=None, payload=None):
        self.warnings.append(msg)
    def error(self, msg, source=None, payload=None):
        pass

class FakeBrowser:
    async def close(self):
        pass

class FakeChromium:
    def __init__(self):
        self.launch_args = None
    async def launch_persistent_context(self, *args, **kwargs):
        self.launch_args = kwargs.get("args")
        return FakeBrowser()

class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()
    async def stop(self):
        pass

class FakeManager:
    def __init__(self):
        self.play = FakePlaywright()
    async def start(self):
        return self.play

@pytest.mark.asyncio
async def test_extension_loaded(tmp_path, monkeypatch):
    ext = tmp_path / "ext.crx"
    ext.write_text("x")
    monkeypatch.setenv("SOLFLARE_CRX", str(ext))
    dummy_log = DummyLog()
    monkeypatch.setattr(helper, "log", dummy_log)
    manager = FakeManager()
    monkeypatch.setattr(helper, "async_playwright", lambda: manager)

    async with PlaywrightHelper(headless=True):
        pass

    assert f"--load-extension={ext}" in manager.play.chromium.launch_args
    assert not dummy_log.warnings

@pytest.mark.asyncio
async def test_extension_missing(tmp_path, monkeypatch):
    ext = tmp_path / "missing.crx"
    monkeypatch.setenv("SOLFLARE_CRX", str(ext))
    dummy_log = DummyLog()
    monkeypatch.setattr(helper, "log", dummy_log)
    manager = FakeManager()
    monkeypatch.setattr(helper, "async_playwright", lambda: manager)

    async with PlaywrightHelper(headless=True):
        pass

    assert manager.play.chromium.launch_args == []
    assert dummy_log.warnings
