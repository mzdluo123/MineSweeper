import typing as T
from mirai.misc import findKey, printer, ImageRegex, getMatchedString
from mirai.event.message.base import BaseMessageComponent, MessageComponentTypes
from pydantic import Field, validator, HttpUrl
from io import BytesIO
from pathlib import Path
from mirai.image import (
    LocalImage,
    IOImage,
    Base64Image, BytesImage,
)
from mirai.logger import Protocol as ProtocolLogger
from aiohttp import ClientSession
import datetime

__all__ = [
    "Plain",
    "Source",
    "At",
    "AtAll",
    "Face",
    "Image",
    "Unknown",
    "Quote",
    "FlashImage"
]

class Plain(BaseMessageComponent):
    type: MessageComponentTypes = "Plain"
    text: str

    def __init__(self, text, **_):
        if len(text) > 128:
            ProtocolLogger.warn(f"mirai does not support for long string: now its length is {len(text)}")
        super().__init__(text=text, type="Plain")

    def toString(self):
        return self.text

class Source(BaseMessageComponent):
    type: MessageComponentTypes = "Source"
    id: int
    time: datetime.datetime

    def toString(self):
        return ""

from .chain import MessageChain

class Quote(BaseMessageComponent):
    type: MessageComponentTypes = "Quote"
    id: T.Optional[int]
    groupId: T.Optional[int]
    senderId: T.Optional[int]
    targetId: T.Optional[int]
    origin: MessageChain

    @validator("origin", always=True, pre=True)
    @classmethod
    def origin_formater(cls, v):
        return MessageChain.parse_obj(v)

    def __init__(self, id: int, groupId: int, senderId: int, origin: int, **_):
        super().__init__(
            id=id,
            groupId=groupId,
            senderId=senderId,
            origin=origin
        )

    def toString(self):
        return ""

class At(BaseMessageComponent):
    type: MessageComponentTypes = "At"
    target: int
    display: T.Optional[str] = None

    def __init__(self, target, display=None, **_):
        super().__init__(target=target, display=display)

    def toString(self):
        return f"[At::target={self.target}]"

class AtAll(BaseMessageComponent):
    type: MessageComponentTypes = "AtAll"

    def __init__(self, **_):
        super().__init__()

    def toString(self):
        return f"[AtAll]"

class Face(BaseMessageComponent):
    type: MessageComponentTypes = "Face"
    faceId: int
    name: T.Optional[str]

    def __init__(self, faceId, name=None, **_):
        super().__init__(faceId=faceId, name=name)

    def toString(self):
        return f"[Face::name={self.name}]"

class Image(BaseMessageComponent):
    type: MessageComponentTypes = "Image"
    imageId: T.Optional[str]
    url: T.Optional[HttpUrl] = None

    @validator("imageId", always=True, pre=True)
    @classmethod
    def imageId_formater(cls, v):
        length = len(v)
        if length == 44:
            # group
            return v[1:-7]
        elif length == 37:
            return v[1:]
        else:
            return v

    def __init__(self, imageId, url=None, **_):
        super().__init__(imageId=imageId, url=url)

    def toString(self):
        return f"[Image::{self.imageId}]"

    def asGroupImage(self) -> str:
        return f"{{{self.imageId}}}.mirai"

    def asFriendImage(self) -> str:
        return self.imageId.upper()

    def asFlashImage(self) -> "FlashImage":
        return FlashImage(self.imageId, self.url)

    @staticmethod
    async def fromRemote(url, **extra) -> BytesImage:
        async with ClientSession() as session:
            async with session.get(url, **extra) as response:
                return BytesImage(await response.read())

    @staticmethod
    def fromFileSystem(path: T.Union[Path, str]) -> LocalImage:
        return LocalImage(path)

    async def toBytes(self, chunk_size=256) -> BytesIO:
        async with ClientSession() as session:
            async with session.get(self.url) as response:
                result = BytesIO()
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    result.write(chunk)
            return result

    @staticmethod
    def fromBytes(data) -> BytesImage:
        return BytesImage(data)

    @staticmethod
    def fromBase64(base64_str) -> Base64Image:
        return Base64Image(base64_str)

    @staticmethod
    def fromIO(IO) -> IOImage:
        return IOImage(IO)

class Xml(BaseMessageComponent):
    type: MessageComponentTypes = "Xml"
    XML: str

    def __init__(self, xml, type="Xml"):
        super().__init__(XML=xml)

class Json(BaseMessageComponent):
    type: MessageComponentTypes = "Json"
    Json: dict = Field(..., alias="json")

    def __init__(self, json: dict, **_):
        super().__init__(Json=json)

class App(BaseMessageComponent):
    type: MessageComponentTypes = "App"
    content: str

    def __init__(self, content: str, **_):
        super().__init__(content=content)

class Poke(BaseMessageComponent):
    type: MessageComponentTypes = "Poke"
    name: str

    def __init__(self, name: str, **_):
        super().__init__(name=name)

class Unknown(BaseMessageComponent):
    type: MessageComponentTypes = "Unknown"
    text: str

    def toString(self):
        return ""

class FlashImage(BaseMessageComponent):
    type: MessageComponentTypes = "FlashImage"
    imageId: T.Optional[str]
    url: T.Optional[HttpUrl] = None

    @validator("imageId", always=True, pre=True)
    @classmethod
    def imageId_formater(cls, v):
        length = len(v)
        if length == 42:
            # group
            return v[1:-5]
        elif length == 37:
            return v[1:]
        else:
            return v

    def __init__(self, imageId, url=None, **_):
        super().__init__(imageId=imageId, url=url)

    def toString(self):
        return f"[FlashImage::{self.imageId}]"

    def asGroupImage(self) -> str:
        return f"{{{self.imageId.upper()}}}.mirai"

    def asFriendImage(self) -> str:
        return self.imageId.upper()

    def asNormal(self) -> Image:
        return Image(self.imageId, self.url)

    @staticmethod
    def fromFileSystem(path: T.Union[Path, str]) -> LocalImage:
        return LocalImage(path, flash=True)

    async def toBytes(self, chunk_size=256) -> BytesIO:
        async with ClientSession() as session:
            async with session.get(self.url) as response:
                result = BytesIO()
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    result.write(chunk)
            return result

    @staticmethod
    def fromBytes(data) -> BytesImage:
        return BytesImage(data, flash=True)

    @staticmethod
    def fromBase64(base64_str) -> Base64Image:
        return Base64Image(base64_str, flash=True)

    @staticmethod
    def fromIO(IO) -> IOImage:
        return IOImage(IO, flash=True)

MessageComponents = {
    "At": At,
    "AtAll": AtAll,
    "Face": Face,
    "Plain": Plain,
    "Image": Image,
    "Source": Source,
    "Quote": Quote,
    "Xml": Xml,
    "Json": Json,
    "App": App,
    "Poke": Poke,
    "FlashImage": FlashImage,
    "Unknown": Unknown
}
