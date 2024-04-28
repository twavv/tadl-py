from __future__ import annotations

from typing import ParamSpec, Callable, Awaitable, cast, Generic, TypeVar

from tadl.query_batch import QueryInstanceBatchLoader
from tadl.descriptor import LazyInitDescriptor
from tadl.query_group import QueryInstanceGroupLoader
from tadl.query_interface import QueryInterface
from tadl.types import TElt, TSelf, TKey

TArg = TypeVar("TArg")
# NOTE:
# Using `TSelf` here are an argument doesn't actually provide much (any?) type
# safety, but it's still useful as a form of documentation.
TQueryMethod = Callable[[TSelf, TArg], Awaitable[list[TElt]]]
TQueryFn = Callable[[TArg], Awaitable[list[TElt]]]

TLoadMethod = Callable[[TSelf, list[TKey]], Awaitable[list[TElt]]]


def query(fn: TQueryMethod[TSelf, TArg, TElt]) -> Query[TArg, TElt]:
    return Query(fn)


class Query(Generic[TArg, TElt]):
    """
    A Query is a wrapper around a data-loading function and several interfaces
    that can be used to load data in different ways.

    The Query (and associated QueryInstance) handle batching related calls
    together for performance and also ensure cache coherency between the
    interfaces to the query.
    """

    def __init__(self, query_fn: TQueryMethod[TSelf, TArg, TElt]) -> None:
        self.__query_fn = query_fn
        self.__interfaces: list[LazyInitDescriptor[QueryInterface[TElt]]] = []

    def __set_name__(self, owner: type, name: str) -> None:
        self.__name = name

    def __get__(self, instance: TSelf, owner: type) -> QueryInstance[TSelf, TArg, TElt]:
        if instance is None:
            raise ValueError(
                "QueryLoaderDescriptor must be accessed through an instance."
            )
        if not hasattr(instance, "__query_loader__"):
            setattr(instance, "__query_loader__", {})  # type: ignore[misc]
        loader_map = cast(
            dict[str, QueryInstance[TSelf, TArg, TElt]],
            instance.__query_loader__,  # type: ignore[attr-defined]
        )
        if self.__name not in loader_map:
            loader_map[self.__name] = QueryInstance(
                instance,
                self.__query_fn,
                [interface.__get__(instance, owner) for interface in self.__interfaces],
            )
        return loader_map[self.__name]

    def batch_interface(
        self,
        *,
        key: Callable[[TElt], TKey],
    ) -> Callable[
        [TLoadMethod[TSelf, TKey, TElt]],
        LazyInitDescriptor[QueryInstanceBatchLoader[TKey, TElt]],
    ]:
        """
        Create a new batch interface for the query.
        """

        def decorator(
            fn: TLoadMethod[TSelf, TKey, TElt],
        ) -> LazyInitDescriptor[QueryInstanceBatchLoader[TKey, TElt]]:
            interface = LazyInitDescriptor(
                lambda instance: QueryInstanceBatchLoader[TKey, TElt](
                    lambda keys: fn(cast(TSelf, instance), keys),
                    key,
                )
            )
            self.__interfaces.append(
                cast(LazyInitDescriptor[QueryInterface[TElt]], interface)
            )
            return interface

        return decorator

    def group_interface(
        self,
        *,
        key: Callable[[TElt], TKey],
        sort: Callable[[TElt], int],
    ) -> Callable[
        [TLoadMethod[TSelf, TKey, TElt]],
        LazyInitDescriptor[QueryInstanceGroupLoader[TKey, TElt]],
    ]:
        """
        Create a new group interface for the query.
        """

        def decorator(
            fn: Callable[[TSelf, list[TKey]], Awaitable[list[TElt]]],
        ) -> LazyInitDescriptor[QueryInstanceGroupLoader[TKey, TElt]]:
            interface = LazyInitDescriptor(
                lambda instance: QueryInstanceGroupLoader[TKey, TElt](
                    lambda keys: fn(cast(TSelf, instance), keys), key, sort
                )
            )
            self.__interfaces.append(
                cast(LazyInitDescriptor[QueryInterface[TElt]], interface)
            )
            return interface

        return decorator


class QueryInstance(Generic[TSelf, TArg, TElt]):
    def __init__(
        self,
        instance: TSelf,
        query_fn: TQueryMethod[TSelf, TArg, TElt],
        interfaces: list[QueryInterface[TElt]],
    ) -> None:
        self.__instance = instance
        self.__query_fn = query_fn
        self.__interfaces = interfaces

    async def query(self, arg: TArg) -> list[TElt]:
        elts = await self.__query_fn(self.__instance, arg)
        for interface in self.__interfaces:
            interface.prime_many(elts)
        return elts

    async def __call__(self, arg: TArg) -> list[TElt]:
        return await self.query(arg)
