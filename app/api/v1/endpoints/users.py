from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(db: SessionDep, user: UserCreate):
    return user_service.create_user(db, user)


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser):
    return current_user
