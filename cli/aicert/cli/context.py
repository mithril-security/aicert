from abc import ABC
from pydantic import BaseModel
from typing import List, Literal, Optional

from .logging import log

class Context(ABC):
    def __init__(self) -> None:
        super().__init__()