import typing as T
from pydantic import BaseModel

from .base import BaseMessageComponent
from mirai.misc import raiser, printer, if_error_print_arg
from .components import Source
from mirai.logger import Protocol

class MessageChain(BaseModel):
    __root__: T.List[BaseMessageComponent] = []

    def __add__(self, value):
        if isinstance(value, BaseMessageComponent):
            self.__root__.append(value)
            return self
        elif isinstance(value, MessageChain):
            self.__root__ += value.__root__
            return self

    def toString(self) -> str:
        return "".join([i.toString() for i in self.__root__])

    @classmethod
    def parse_obj(cls, obj):
        from .components import MessageComponents
        result = []
        for i in obj:
            if not isinstance(i, dict):
                raise TypeError("invaild value")
            try:
                result.append(MessageComponents[i['type']].parse_obj(i))
            except:
                Protocol.error(f"error throwed by message serialization: {i['type']}, it's {i}")
                raise
        return cls(__root__=result)

    def __iter__(self):
        yield from self.__root__

    def __getitem__(self, index):
        return self.__root__[index]

    def hasComponent(self, component_class) -> bool:
        for i in self:
            if type(i) == component_class:
                return True
        else:
            return False

    def __len__(self) -> int:
        return len(self.__root__)

    def getFirstComponent(self, component_class) -> T.Optional[BaseMessageComponent]:
        for i in self:
            if type(i) == component_class:
                return i

    def getAllofComponent(self, component_class) -> T.List[BaseMessageComponent]:
        return [i for i in self if type(i) == component_class]

    def getSource(self) -> Source:
        return self.getFirstComponent(Source)

    __contains__ = hasComponent
    __getitem__ = getAllofComponent