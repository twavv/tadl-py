from __future__ import annotations

from typing import Generic, Callable, Awaitable, cast

import strawberry.dataloader

from tadl.descriptor import LazyInitDescriptor
from tadl.types import TKey, TElt, TSelf

BatchLoadFn = Callable[[TSelf, list[TKey]], Awaitable[list[TElt]]]


def batch_loader() -> (
    Callable[
        [BatchLoadFn[TSelf, TKey, TElt]], LazyInitDescriptor[BatchLoader[TKey, TElt]]
    ]
):
    """
    A method decorator that transforms a function into a BatchLoader.
    """

    def decorator(
        fn: BatchLoadFn[TSelf, TKey, TElt]
    ) -> LazyInitDescriptor[BatchLoader[TKey, TElt]]:
        interface = LazyInitDescriptor(
            lambda instance: BatchLoader[TKey, TElt](
                lambda keys: fn(cast(TSelf, instance), keys),
            )
        )
        return interface

    return decorator


class BatchLoader(Generic[TKey, TElt]):
    """
    A generic data loader object that batches calls to a load function.

    This exists separate of the ``Query``/``QueryInterface`` functionality
    provided by TADL.
    """

    def __init__(
        self,
        load_fn: Callable[[list[TKey]], Awaitable[list[TElt]]],
    ) -> None:
        self.__load_fn = load_fn
        self.__dl: strawberry.dataloader.DataLoader[TKey, TElt] = (
            strawberry.dataloader.DataLoader(self.__load)
        )

    async def __load(self, keys: list[TKey]) -> list[TElt]:
        return await self.__load_fn(keys)

    def __call__(self, key: TKey) -> Awaitable[TElt]:
        """
        Load a single group of elements by key.

        This is a convenience method that wraps the `load` method.
        """
        return self.load(key)

    async def load(self, key: TKey) -> TElt:
        return await self.__dl.load(key)

    async def load_many(self, keys: list[TKey]) -> list[TElt]:
        return await self.__dl.load_many(keys)

