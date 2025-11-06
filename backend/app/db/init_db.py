from ..core.db import engine
from ..models.base import Base
from ..models import todo, todo_audit, user  # noqa: F401


def create_all() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_all()
