from . import InternalEvent
from pydantic import BaseModel
from mirai import Mirai

class UnexpectedException(BaseModel):
    error: Exception
    event: InternalEvent
    application: Mirai

    class Config:
        arbitrary_types_allowed = True