from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


# The leading _ in _apply_filters is a Python convention meaning "internal to this module". Routes shouldn't call it.
def _apply_filters(stmt, completed: bool | None):
    if completed is not None:
        stmt = stmt.where(Task.completed == completed)
    return stmt


def count_tasks(db: Session, completed: bool | None = None) -> int:
    stmt = _apply_filters(select(func.count()).select_from(Task), completed)
    return db.execute(stmt).scalar_one()


def list_tasks(
    db: Session, limit: int, offset: int, completed: bool | None = None
) -> list[Task]:
    stmt = select(Task)
    stmt = _apply_filters(stmt, completed)
    stmt = stmt.order_by(Task.id).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


def get_task(db: Session, task_id: int) -> Task | None:
    return db.get(Task, task_id)


def create_task(db: Session, task_in: TaskCreate) -> Task:
    task = Task(**task_in.model_dump())
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
