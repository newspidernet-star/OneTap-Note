from io import BytesIO


async def test_create_session(client):
    resp = await client.post("/api/sessions", json={"title": "物理课"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "物理课"
    assert resp.json()["status"] == "created"


async def test_upload_and_list(client):
    s = await client.post("/api/sessions", json={"title": "T"})
    sid = s.json()["id"]

    resp = await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 0},
        files={"file": ("lec.mp4", BytesIO(b"fake"), "video/mp4")},
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "video"

    resp = await client.post(
        "/api/media/upload",
        data={"session_id": sid, "sort_order": 1},
        files={"file": ("slide.png", BytesIO(b"fake"), "image/png")},
    )
    assert resp.json()["type"] == "image"

    materials = await client.get(f"/api/media/session/{sid}/materials")
    assert len(materials.json()) == 2
    assert materials.json()[0]["sort_order"] == 0
    assert materials.json()[1]["sort_order"] == 1
