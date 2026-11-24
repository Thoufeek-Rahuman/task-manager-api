class AppError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass
