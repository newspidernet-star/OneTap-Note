async def test_transcribe_no_material(client):
    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]
    resp = await client.post(f"/api/speech/transcribe/{sid}")
    assert resp.status_code == 404
