from typing import Generic, Callable, Awaitable, TypeVar

import strawberry.dataloader

from tadl.query_interface import QueryInterface
from tadl.types import TKey, TElt
from tadl.match import match_array


class QueryInstanceBatchLoader(QueryInterface[TElt], Generic[TKey, TElt]):
    """
    QueryInstanceBatchLoader is a QueryInterface for a QueryInstance that takes
    a list of keys and one item for each key.
    """

    def __init__(
        self,
        load_fn: Callable[[list[TKey]], Awaitable[list[TElt]]],
        key_fn: Callable[[TElt], TKey],
    ) -> None:
        self.__load_fn = load_fn
        self.__key_fn = key_fn
        self.__dl: strawberry.dataloader.DataLoader[TKey, TElt | None] = (
            strawberry.dataloader.DataLoader(self.__load)
        )

    async def __load(self, keys: list[TKey]) -> list[TElt | None]:
        elts = await self.__load_fn(keys)
        return match_array(keys, elts, key=self.__key_fn)

    async def __call__(self, key: TKey) -> TElt | None:
        """
        Load a single element by key.

        This is a convenience method that wraps the `load` method.
        """
        return await self.__dl.load(key)

    def prime_many(self, elts: list[TElt]) -> None:
        """
        Prime the cache with the given elements.
        """
        self.__dl.prime_many({self.__key_fn(elt): elt for elt in elts})

    async def load(self, key: TKey) -> TElt | None:
        """
        Load a single element by key.
        """
        return await self.__dl.load(key)

    async def load_many(self, keys: list[TKey]) -> list[TElt | None]:
        """
        Load many elements by key.

        The resulting list will have the same order as the input list (including
        ``None`` values for keys that were not found).
        """
        return await self.__dl.load_many(keys)


T = TypeVar("T")
