async def test_quick_capture_saves_link_without_downloading(client):
    response = await client.post(
        "/api/sessions/quick-capture",
        json={
            "url": "https://example.com/video/42",
            "note": "音效和转场很好，以后做产品视频时参考。",
            "client_id": "quick-client",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    session = payload["session"]
    material = payload["material"]
    assert session["status"] == "done"
    assert session["title"].startswith("音效和转场很好")
    assert session["user_note"] == "音效和转场很好，以后做产品视频时参考。"
    assert material["type"] == "link"
    assert material["source"] == "quick_capture"
    assert material["url"] is None
    assert material["original_url"] == "https://example.com/video/42"

    materials = await client.get(f"/api/media/session/{session['id']}/materials")
    assert materials.status_code == 200
    assert materials.json()[0]["original_url"] == "https://example.com/video/42"


async def test_quick_capture_exports_lightweight_markdown(client):
    created = await client.post(
        "/api/sessions/quick-capture",
        json={
            "url": "https://example.com/video/42",
            "note": "音效层次很适合作为剪辑参考。",
        },
    )
    session_id = created.json()["session"]["id"]

    exported = await client.get(f"/api/summary/export/{session_id}?view=note")
    assert exported.status_code == 200
    markdown = exported.json()["markdown"]
    assert "type: quick-capture" in markdown
    assert "## 我为什么留下" in markdown
    assert "音效层次很适合作为剪辑参考。" in markdown
    assert "[原视频 / 原始链接](https://example.com/video/42)" in markdown
