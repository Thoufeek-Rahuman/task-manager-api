from fastapi import FastAPI, HTTPException, status, Query
from typing import Annotated
from pydantic import BaseModel
    

app = FastAPI()


tasks = [
    {"id": 1, "title": "Buy groceries", "completed": False},
    {"id": 2, "title": "Learn FastAPI path parameters", "completed": True},
    {"id": 3, "title": "Read about query parameters", "completed": False},
    {"id": 4, "title": "Write unit tests", "completed": False},
    {"id": 5, "title": "Deploy the API", "completed": False},
]

class TaskCreate(BaseModel):
    title: str
    completed: bool = False

class Task(TaskCreate):
    id: int

@app.get('/')
def root():
    return {"message": "Hello from fast api"}


@app.get('/tasks/{task_id}', response_model=Task)
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

# def get_tasks(limit: int = Query(5, ge=1, le=100), completed: bool | None = None):
#     if completed is None:
#         return tasks[:limit]    
#     result = [task for task in tasks if task["completed"] == completed]
#     return result[:limit]

#This is the fastAPI new version of Annotated
@app.get('/tasks', response_model=list[Task])
def get_tasks(limit: Annotated[int, Query(ge=1, le=100)] = 5, completed: bool | None = None):
    if completed is None:
        return tasks[:limit]
    result = [task for task in tasks if task["completed"] == completed]
    return result[:limit]


@app.post('/tasks', response_model=Task, status_code=status.HTTP_201_CREATED)    
def create_task(task: TaskCreate):
    new_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": new_id, **task.model_dump()}
    tasks.append(new_task)
    return new_task

@app.put('/tasks/{task_id}', response_model=Task)
def update_task(task_id: int, task_update: TaskCreate):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks[i].update(task_update.model_dump())
            return tasks[i]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
