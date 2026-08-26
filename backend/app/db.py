from sqlmodel import SQLModel, create_engine, Session

from app.config import settings
from app.models import models  # noqa: F401 - import registers tables with SQLModel.metadata

engine = create_engine(settings.DATABASE_URL, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
