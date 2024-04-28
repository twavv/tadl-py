from __future__ import annotations

import dataclasses
from typing import Callable, reveal_type

import pytest

import tadl

pytestmark = pytest.mark.asyncio


async def test_example_page_service() -> None:
    ps = PageService()

    ps.add_page(Page(id=1, slug="a", user_id=1))
    ps.add_page(Page(id=2, slug="b", user_id=1))
    ps.add_page(Page(id=3, slug="c", user_id=2))
    ps.add_page(Page(id=4, slug="d", user_id=2))

    pages_by_id = await ps.by_id.load_many([1, 2, 3, 4])
    assert len(pages_by_id) == 4
    assert [page.id if page else None for page in pages_by_id] == [1, 2, 3, 4]
    assert ps.query_count == 1

    pages_by_slug = await ps.by_slug.load_many(["a", "b", "c", "d"])
    assert len(pages_by_slug) == 4
    assert [page.id if page else None for page in pages_by_slug] == [1, 2, 3, 4]
    assert (
        ps.query_count == 1
    ), "by_slug should not trigger new queries when given seen slugs"

    pages_by_id = await ps.by_id.load_many([1, 5])
    assert len(pages_by_id) == 2
    assert [page.id if page else None for page in pages_by_id] == [1, None]
    assert ps.query_count == 2, "by_id should trigger new queries when given unseen ids"

    pages_for_user = await ps.for_user.load(2)
    assert len(pages_for_user) == 2
    assert [page.id if page else None for page in pages_for_user] == [3, 4]
    assert (
        ps.query_count == 3
    ), "for_user should trigger new queries when given unseen user_ids"

    await ps.for_user.load(2)
    assert (
        ps.query_count == 3
    ), "for_user should not trigger new queries when given seen user_ids"


class PageService:
    def __init__(self) -> None:
        self.query_count = 0
        self.__data = list[Page]()

    def add_page(self, page: Page) -> None:
        self.__data.append(page)

    @tadl.query
    async def __query(self, filter: Callable[[Page], bool]) -> list[Page]:
        self.query_count += 1
        return [page for page in self.__data if filter(page)]

    @__query.batch_interface(key=lambda page: page.id)
    async def by_id(self, ids: list[int]) -> list[Page]:
        return await self.__query(lambda page: page.id in ids)

    @__query.batch_interface(key=lambda page: page.slug)
    async def by_slug(self, slugs: list[str]) -> list[Page]:
        return await self.__query(lambda page: page.slug in slugs)

    @__query.group_interface(key=lambda page: page.user_id, sort=lambda page: page.id)
    async def for_user(self, user_ids: list[int]) -> list[Page]:
        return await self.__query(lambda page: page.user_id in user_ids)


@dataclasses.dataclass
class Page:
    id: int
    slug: str
    user_id: int
