from types import SimpleNamespace

import app.services.tunnel as tunnel
from app.services.tunnel import _extract_quick_tunnel_url


def test_extract_quick_tunnel_url_ignores_cloudflare_api_host():
    text = "Requesting tunnel from https://api.trycloudflare.com then https://knight-gains-eden-eric.trycloudflare.com"

    assert _extract_quick_tunnel_url(text) == "https://knight-gains-eden-eric.trycloudflare.com"


def test_extract_quick_tunnel_url_returns_none_for_api_host_only():
    assert _extract_quick_tunnel_url("POST https://api.trycloudflare.com") is None


class _RunningProcess:
    def poll(self):
        return None


def _auto_tunnel_settings():
    return SimpleNamespace(public_base_url=None, tunnel="auto")


def test_preflight_reuses_healthy_tunnel(monkeypatch):
    current = "https://healthy.trycloudflare.com"
    monkeypatch.setattr(tunnel, "get_settings", _auto_tunnel_settings)
    monkeypatch.setattr(tunnel, "_TUNNEL_URL", current)
    monkeypatch.setattr(tunnel, "_PROC", _RunningProcess())
    monkeypatch.setattr(tunnel, "_LOCAL_PROBE_SUPPORTED", True)
    monkeypatch.setattr(tunnel, "_hostname_resolves", lambda _url: True)
    monkeypatch.setattr(tunnel, "_probe_tunnel", lambda _url: True)
    monkeypatch.setattr(
        tunnel,
        "reset_tunnel",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected reset")),
    )

    assert tunnel.ensure_public_base_url() == current


def test_preflight_rebuilds_dns_stale_tunnel(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel, "get_settings", _auto_tunnel_settings)
    monkeypatch.setattr(tunnel, "_TUNNEL_URL", "https://stale.trycloudflare.com")
    monkeypatch.setattr(tunnel, "_PROC", _RunningProcess())
    monkeypatch.setattr(tunnel, "_hostname_resolves", lambda _url: False)
    monkeypatch.setattr(tunnel, "reset_tunnel", lambda: events.append("reset"))
    monkeypatch.setattr(
        tunnel,
        "start_tunnel",
        lambda: events.append("start") or "https://new.trycloudflare.com",
    )

    assert tunnel.ensure_public_base_url() == "https://new.trycloudflare.com"
    assert events == ["reset", "start"]


def test_preflight_rebuilds_tunnel_that_stops_responding(monkeypatch):
    events = []
    monkeypatch.setattr(tunnel, "get_settings", _auto_tunnel_settings)
    monkeypatch.setattr(tunnel, "_TUNNEL_URL", "https://was-healthy.trycloudflare.com")
    monkeypatch.setattr(tunnel, "_PROC", _RunningProcess())
    monkeypatch.setattr(tunnel, "_LOCAL_PROBE_SUPPORTED", True)
    monkeypatch.setattr(tunnel, "_hostname_resolves", lambda _url: True)
    monkeypatch.setattr(tunnel, "_probe_tunnel", lambda _url: False)
    monkeypatch.setattr(tunnel, "reset_tunnel", lambda: events.append("reset"))
    monkeypatch.setattr(
        tunnel,
        "start_tunnel",
        lambda: events.append("start") or "https://replacement.trycloudflare.com",
    )

    assert tunnel.ensure_public_base_url() == "https://replacement.trycloudflare.com"
    assert events == ["reset", "start"]


def test_preflight_does_not_rebuild_when_local_https_probe_is_unsupported(monkeypatch):
    current = "https://provider-reachable.trycloudflare.com"
    monkeypatch.setattr(tunnel, "get_settings", _auto_tunnel_settings)
    monkeypatch.setattr(tunnel, "_TUNNEL_URL", current)
    monkeypatch.setattr(tunnel, "_PROC", _RunningProcess())
    monkeypatch.setattr(tunnel, "_LOCAL_PROBE_SUPPORTED", None)
    monkeypatch.setattr(tunnel, "_hostname_resolves", lambda _url: True)
    monkeypatch.setattr(tunnel, "_probe_tunnel", lambda _url: False)
    monkeypatch.setattr(
        tunnel,
        "reset_tunnel",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected reset")),
    )

    assert tunnel.ensure_public_base_url() == current
    assert tunnel._LOCAL_PROBE_SUPPORTED is False
