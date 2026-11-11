from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


def list_tasks(db: Session, limit: int, completed: bool | None = None) -> list[Task]:
    stmt = select(Task)
    if completed is not None:
        stmt = stmt.where(Task.completed == completed)
    stmt = stmt.order_by(Task.id).limit(limit)
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
