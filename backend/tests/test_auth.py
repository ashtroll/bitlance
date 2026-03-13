import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register
        reg = await client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPass123!",
            "role": "freelancer",
            "full_name": "Test User"
        })
        assert reg.status_code == 201
        data = reg.json()
        assert "access_token" in data
        assert data["user"]["role"] == "freelancer"

        # Login
        login = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!"
        })
        assert login.status_code == 200
        assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_duplicate_registration():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "email": "dup@example.com",
            "username": "dupuser",
            "password": "TestPass123!",
            "role": "employer"
        }
        await client.post("/auth/register", json=payload)
        r2 = await client.post("/auth/register", json=payload)
        assert r2.status_code == 400
