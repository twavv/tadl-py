import datetime
from typing import TypeVar

Scalar = int | float | str | bool | datetime.datetime | tuple["Scalar", ...]
TKey = TypeVar("TKey", bound=Scalar)
TElt = TypeVar("TElt")
TSelf = TypeVar("TSelf")
