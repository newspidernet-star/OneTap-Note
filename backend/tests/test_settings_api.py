from app.models import ApiSettings


async def test_list_settings_empty(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    assert data[0]["is_set"] is False
    assert data[0]["is_required"] is True


async def test_update_and_list_settings(client):
    await client.post("/api/settings", json={
        "settings": [{"key": "deepseek_api_key", "value": "sk-test123", "is_required": True}]
    })
    resp = await client.get("/api/settings")
    deepseek = [s for s in resp.json() if s["key"] == "deepseek_api_key"][0]
    assert deepseek["is_set"] is True


async def test_test_setting(client):
    await client.post("/api/settings", json={
        "settings": [{"key": "deepseek_api_key", "value": "sk-test123", "is_required": True}]
    })
    resp = await client.post("/api/settings/deepseek_api_key/test")
    assert resp.json()["ok"] is True


async def test_test_setting_not_configured(client):
    resp = await client.post("/api/settings/volcano_app_id/test")
    assert resp.json()["ok"] is False