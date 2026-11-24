from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


# The leading _ in _apply_filters is a Python convention meaning "internal to this module". Routes shouldn't call it.
def _apply_filters(stmt, completed: bool | None, owner_id: int):
    if completed is not None:
        stmt = stmt.where(Task.completed == completed)
    return stmt.where(Task.user_id == owner_id)


def count_tasks(db: Session, owner_id: int, completed: bool | None = None) -> int:
    stmt = _apply_filters(select(func.count()).select_from(Task), completed, owner_id)
    return db.execute(stmt).scalar_one()


def list_tasks(
    db: Session,
    limit: int,
    offset: int,
    owner_id: int,
    completed: bool | None = None,
) -> list[Task]:
    stmt = select(Task)
    stmt = _apply_filters(stmt, completed, owner_id)
    stmt = stmt.order_by(Task.id).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


def get_task(db: Session, task_id: int, owner_id: int) -> Task:
    stmt = select(Task).where(Task.id == task_id, Task.user_id == owner_id)
    task = db.scalar(stmt)
    if task is None:
        raise NotFoundError("Task not Found")
    return task


def create_task(db: Session, task_in: TaskCreate, owner_id: int) -> Task:
    task = Task(**task_in.model_dump(), user_id=owner_id)
    db.add(task)
    db.commit()
    return task


def update_task(db: Session, task: Task, task_in: TaskCreate) -> Task:
    for field, value in task_in.model_dump().items():
        setattr(task, field, value)
    db.commit()
    return task


def partial_update_task(db: Session, task: Task, task_in: TaskUpdate) -> Task:
    for field, value in task_in.model_dump(
        exclude_unset=True, exclude_none=True
    ).items():
        setattr(task, field, value)
    db.commit()
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()
