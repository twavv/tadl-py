from typing import Generic, Callable, Awaitable, TypeVar, reveal_type

import strawberry.dataloader

from tadl.query_interface import QueryInterface
from tadl.types import TKey, TElt, Scalar
from tadl.match import match_array, group_array


class QueryInstanceGroupLoader(QueryInterface[TElt], Generic[TKey, TElt]):
    """
    QueryInstanceGroupLoader is a QueryInterface for a QueryInstance that takes
    a list of keys and returns a list of items for each key.
    """

    def __init__(
        self,
        load_fn: Callable[[list[TKey]], Awaitable[list[TElt]]],
        key_fn: Callable[[TElt], TKey],
        sort_fn: Callable[[TElt], Scalar],
    ) -> None:
        self.__load_fn = load_fn
        self.__key_fn = key_fn
        self.__sort_fn = sort_fn
        self.__dl: strawberry.dataloader.DataLoader[TKey, list[TElt]] = (
            strawberry.dataloader.DataLoader(self.__load)
        )

    async def __load(self, keys: list[TKey]) -> list[list[TElt]]:
        elts = await self.__load_fn(keys)
        return group_array(keys, elts, key=self.__key_fn, sort=self.__sort_fn)

    def __call__(self, key: TKey) -> Awaitable[list[TElt]]:
        """
        Load a single group of elements by key.

        This is a convenience method that wraps the `load` method.
        """
        return self.load(key)

    async def load(self, key: TKey) -> list[TElt]:
        return await self.__dl.load(key)

    async def load_many(self, keys: list[TKey]) -> list[list[TElt]]:
        return await self.__dl.load_many(keys)

    def prime_many(self, elts: list[TElt]) -> None:
        # The prime has to be a no-op because even if we see elements that
        # belong to the group, we still need to go to the source of truth to
        # make sure that we have *all* of the elements.
        pass


T = TypeVar("T")
