import importlib

import wskr.config as cfg


def test_config_env_and_kwargs(monkeypatch):
    monkeypatch.setenv("WSKR_TIMEOUT_S", "5")
    importlib.reload(cfg)
    assert cfg.TIMEOUT_S == 5
    cfg.configure(timeout_s=2, dark_mode_policy="force-on")
    assert cfg.TIMEOUT_S == 2
    assert cfg.DARK_MODE_POLICY == "force-on"
    cfg.configure(timeout_s=1.0, dark_mode_policy="auto")
