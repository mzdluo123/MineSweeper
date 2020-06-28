from pydantic import BaseModel
import typing as T
from mirai.depend import Depend

class ExecutorProtocol(BaseModel):
    callable: T.Callable
    dependencies: T.List[Depend]
    middlewares: T.List

    class Config:
        arbitrary_types_allowed = True