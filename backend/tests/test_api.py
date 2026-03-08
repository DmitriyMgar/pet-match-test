from __future__ import annotations

from httpx import AsyncClient

GOOD_PROFILE = {
    "apartment_size_m2": 80,
    "has_children": False,
    "monthly_budget_rub": 50000,
    "work_hours_per_day": 8,
}

BAD_PROFILE = {
    "apartment_size_m2": 10,
    "has_children": True,
    "monthly_budget_rub": 2000,
    "work_hours_per_day": 12,
}


# --- Evaluate ---


async def test_evaluate_compatible(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": GOOD_PROFILE},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["compatible"] is True
    assert data["risk_level"] == "low"
    assert data["risk_score"] == 0
    assert len(data["positives"]) > 0
    assert data["reasons"] == []


async def test_evaluate_incompatible(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": BAD_PROFILE},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["compatible"] is False
    assert data["risk_level"] == "high"
    assert data["risk_score"] >= 10
    assert len(data["reasons"]) > 0


async def test_evaluate_unknown_pet_type(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dragon", "profile": GOOD_PROFILE},
    )
    assert resp.status_code == 404


async def test_evaluate_returns_alternatives(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": BAD_PROFILE},
    )
    data = resp.json()
    assert data["compatible"] is False
    for alt in data["alternatives"]:
        assert "pet_type" in alt
        assert "name" in alt
        assert "why" in alt


# --- Pet types ---


async def test_pet_types(async_client: AsyncClient):
    resp = await async_client.get("/api/pet-types")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    ids = {item["id"] for item in data}
    assert ids == {"dog", "cat", "fish"}


# --- Rules ---


async def test_get_rules(async_client: AsyncClient):
    resp = await async_client.get("/api/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules_version" in data
    assert "scoring" in data
    assert "common_rules" in data
    assert "pet_types" in data


async def test_reload_success(async_client: AsyncClient):
    resp = await async_client.post("/api/rules/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "rules_version" in data


async def test_reload_broken_yaml(async_client: AsyncClient, tmp_path):
    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": GOOD_PROFILE},
    )
    assert resp.status_code == 200

    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text("scoring:\n  thresholds: invalid", encoding="utf-8")

    resp = await async_client.post("/api/rules/reload")
    assert resp.status_code == 422

    resp = await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": GOOD_PROFILE},
    )
    assert resp.status_code == 200
    assert resp.json()["compatible"] is True


async def test_validate_valid(async_client: AsyncClient):
    resp = await async_client.post("/api/rules/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


async def test_validate_invalid(async_client: AsyncClient, tmp_path):
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text("scoring:\n  thresholds: invalid", encoding="utf-8")

    resp = await async_client.post("/api/rules/validate")
    assert resp.status_code == 422


# --- Rules raw & save ---


async def test_get_rules_raw(async_client: AsyncClient):
    resp = await async_client.get("/api/rules/raw")
    assert resp.status_code == 200
    assert "scoring" in resp.text
    assert "pet_types" in resp.text


async def test_save_rules_valid(async_client: AsyncClient):
    raw = (await async_client.get("/api/rules/raw")).text
    resp = await async_client.post("/api/rules", json={"yaml_content": raw})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "rules_version" in resp.json()


async def test_save_rules_invalid(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/rules",
        json={"yaml_content": "scoring:\n  thresholds: invalid"},
    )
    assert resp.status_code == 422


# --- Stats ---


async def test_stats_empty(async_client: AsyncClient):
    resp = await async_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 0
    assert data["compatible_count"] == 0
    assert data["incompatible_count"] == 0


async def test_stats_after_evaluations(async_client: AsyncClient):
    await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": GOOD_PROFILE},
    )
    await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": BAD_PROFILE},
    )
    await async_client.post(
        "/api/evaluate",
        json={"pet_type": "cat", "profile": GOOD_PROFILE},
    )

    resp = await async_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert data["compatible_count"] == 2
    assert data["incompatible_count"] == 1
    assert data["today_count"] == 3
    assert data["by_pet_type"]["dog"] == 2
    assert data["by_pet_type"]["cat"] == 1


# --- Evaluations list ---


async def test_evaluations_empty(async_client: AsyncClient):
    resp = await async_client.get("/api/evaluations")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_evaluations_pagination(async_client: AsyncClient):
    for _ in range(5):
        await async_client.post(
            "/api/evaluate",
            json={"pet_type": "fish", "profile": GOOD_PROFILE},
        )

    resp = await async_client.get("/api/evaluations?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    resp = await async_client.get("/api/evaluations?limit=2&offset=4")
    data = resp.json()
    assert len(data) == 1


async def test_evaluation_record_fields(async_client: AsyncClient):
    await async_client.post(
        "/api/evaluate",
        json={"pet_type": "dog", "profile": GOOD_PROFILE},
    )

    resp = await async_client.get("/api/evaluations")
    data = resp.json()
    assert len(data) == 1

    record = data[0]
    assert record["pet_type"] == "dog"
    assert record["compatible"] is True
    assert record["risk_level"] == "low"
    assert "profile" in record
    assert "reasons" in record
    assert "positives" in record
    assert "alternatives" in record
    assert "rules_version" in record
    assert "created_at" in record


# --- Health ---


async def test_health(async_client: AsyncClient):
    resp = await async_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
