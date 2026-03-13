from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.project import Project


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id) -> Project | None:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.milestones))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
