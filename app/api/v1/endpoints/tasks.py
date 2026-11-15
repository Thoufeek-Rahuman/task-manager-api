from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.schemas.task import Task, TaskCreate, TaskPage, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=TaskPage)
def get_tasks(
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
    offset: Annotated[int, Query(ge=0)] = 0,
    completed: bool | None = None,
):
    items = task_service.list_tasks(db, limit, offset, completed)
    total = task_service.count_tasks(db, completed)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{task_id}", response_model=Task)
def get_task(db: SessionDep, task_id: int):
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not Found"
        )
    return task


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(db: SessionDep, task_in: TaskCreate):
    task = task_service.create_task(db, task_in)
    return task


@router.put("/{task_id}", response_model=Task)
def update_task(db: SessionDep, task_id: int, task_update: TaskCreate):
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not Found"
        )
    task = task_service.update_task(db, task, task_update)
    return task


@router.patch("/{task_id}", response_model=Task)
def patch_task(db: SessionDep, task_id: int, task_update: TaskUpdate):

    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not Found"
        )
    task = task_service.partial_update_task(db, task, task_update)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(db: SessionDep, task_id: int):
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not Found"
        )
    task_service.delete_task(db, task)
