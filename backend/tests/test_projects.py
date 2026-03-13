import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def get_employer_token(client: AsyncClient) -> str:
    r = await client.post("/auth/register", json={
        "email": "emp@proj.test",
        "username": "emptest",
        "password": "TestPass123!",
        "role": "employer",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await get_employer_token(client)
        r = await client.post("/projects/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Test Blog Platform",
                "description": "Build a blog with authentication, post creation, and admin panel.",
                "total_budget": 3000.0,
            }
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Test Blog Platform"
        assert len(data["milestones"]) >= 2
        assert data["ai_roadmap"] is not None
