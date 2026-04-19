from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch, aiohttp_client):
    db_path = tmp_path / "portal-test.db"
    monkeypatch.setenv("PORTAL_DB_PATH", str(db_path))
    monkeypatch.setenv("OWNER_USERNAME", "DANGER")
    monkeypatch.setenv("OWNER_PASSWORD", "Aa@123456")

    from core.config import Config
    from core.database import db

    Config.DB_PATH = Path(db_path)
    db.db_path = Path(db_path)

    from app_new import init_app

    app = await init_app()
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_member_registration_and_login_flow(client):
    register_response = await client.post(
        "/api/auth/register",
        json={
            "game_name": "FrostWolf",
            "email": "member@example.com",
            "state": "TNT-100",
            "player_power": 1234567,
            "specialization": "Marksman",
            "discord_id": "frostwolf",
            "password": "StrongPass1!",
        },
    )
    assert register_response.status == 201
    register_payload = await register_response.json()
    assert register_payload["success"] is True

    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "member@example.com",
            "password": "StrongPass1!",
            "login_type": "member",
        },
    )
    assert login_response.status == 200
    login_payload = await login_response.json()
    assert login_payload["redirect"] == "/portal"

    portal_response = await client.get("/portal")
    assert portal_response.status == 200
    portal_text = await portal_response.text()
    assert "بوابة أعضاء TNT" in portal_text


@pytest.mark.asyncio
async def test_calculator_and_ai_api_for_member(client):
    await client.post(
        "/api/auth/register",
        json={
            "game_name": "BearHunter",
            "email": "hunter@example.com",
            "state": "TNT-200",
            "player_power": 2233445,
            "specialization": "Infantry",
            "password": "StrongPass1!",
        },
    )
    await client.post(
        "/api/auth/login",
        json={
            "email": "hunter@example.com",
            "password": "StrongPass1!",
            "login_type": "member",
        },
    )

    calc_response = await client.post(
        "/api/calculators/troops",
        json={"troop_type": "infantry", "tier": 7, "count": 1000, "speed_bonus_percent": 10},
    )
    assert calc_response.status == 200
    calc_payload = await calc_response.json()
    assert calc_payload["success"] is True
    assert calc_payload["result"]["resources"]["food"] > 0

    ai_response = await client.post(
        "/api/ai/chat",
        json={"question": "ما أفضل ترتيب للدب وما البحث المناسب لي؟"},
    )
    assert ai_response.status == 200
    ai_payload = await ai_response.json()
    assert ai_payload["success"] is True
    assert "تحليل المساعد الخبير" in ai_payload["answer"]


@pytest.mark.asyncio
async def test_owner_can_create_state_and_manage_dashboard(client):
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "DANGER", "password": "Aa@123456", "login_type": "member"},
    )
    assert login_response.status == 200

    create_response = await client.post(
        "/owner/states/create",
        data={
            "state_name": "TNT State",
            "state_number": "321",
            "contact_email": "state321@example.com",
            "password": "StatePass1!",
            "description": "Primary alliance state",
        },
    )
    assert create_response.status in {200, 302}

    owner_page = await client.get("/owner")
    assert owner_page.status == 200
    owner_text = await owner_page.text()
    assert "لوحة تحكم المالك" in owner_text
    assert "TNT State" in owner_text


@pytest.mark.asyncio
async def test_state_login_from_main_flow(client):
    await client.post(
        "/api/auth/login",
        json={"email": "DANGER", "password": "Aa@123456", "login_type": "member"},
    )
    await client.post(
        "/owner/states/create",
        data={
            "state_name": "State Login",
            "state_number": "654",
            "contact_email": "state654@example.com",
            "password": "StatePass1!",
            "description": "State login test",
        },
    )

    state_client = client
    login_response = await state_client.post(
        "/api/auth/login",
        json={"email": "state654@example.com", "password": "StatePass1!", "login_type": "state"},
    )
    assert login_response.status == 200
    login_payload = await login_response.json()
    assert login_payload["redirect"] == "/state-portal"

    state_portal = await state_client.get("/state-portal")
    assert state_portal.status == 200
    state_text = await state_portal.text()
    assert "بوابة الولاية" in state_text