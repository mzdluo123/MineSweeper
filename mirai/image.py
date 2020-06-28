from pathlib import Path
from abc import ABCMeta, abstractmethod
import base64

class InternalImage(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self):
        super().__init__()

    @abstractmethod
    def render(self) -> bytes:
        pass

class LocalImage(InternalImage):
    path: Path
    flash: bool = False

    def __init__(self, path, flash: bool = False):
        if isinstance(path, str):
            self.path = Path(path)
        elif isinstance(path, Path):
            self.path = path
        self.flash = flash

    def render(self) -> bytes:
        return self.path.read_bytes()

class IOImage(InternalImage):
    def __init__(self, IO, flash: bool = False):
        """make a object with 'read' method a image.

        IO - a object, must has a `read` method to return bytes.
        """
        self.IO = IO
        self.flash = flash

    def render(self) -> bytes:
        return self.IO.getvalue()

class BytesImage(InternalImage):
    def __init__(self, data: bytes, flash: bool = False):
        self.data = data
        self.flash = flash

    def render(self) -> bytes:
        return self.data

class Base64Image(InternalImage):
    def __init__(self, base64_str, flash: bool = False):
        self.base64_str = base64_str
        self.flash = flash
    
    def render(self) -> bytes:
        return base64.b64decode(self.base64_str)
