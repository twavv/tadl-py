import abc
from typing import Generic

from tadl.types import TElt


class QueryInterface(abc.ABC, Generic[TElt]):
    @abc.abstractmethod
    def prime_many(self, elts: list[TElt]) -> None:
        pass
