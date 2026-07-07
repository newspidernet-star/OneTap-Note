from app.services.tunnel import _extract_quick_tunnel_url


def test_extract_quick_tunnel_url_ignores_cloudflare_api_host():
    text = "Requesting tunnel from https://api.trycloudflare.com then https://knight-gains-eden-eric.trycloudflare.com"

    assert _extract_quick_tunnel_url(text) == "https://knight-gains-eden-eric.trycloudflare.com"


def test_extract_quick_tunnel_url_returns_none_for_api_host_only():
    assert _extract_quick_tunnel_url("POST https://api.trycloudflare.com") is None
