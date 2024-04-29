from __future__ import annotations

import dataclasses
from typing import Callable, reveal_type, Literal

import pytest

import tadl

pytestmark = pytest.mark.asyncio


async def test_query_paramspec() -> None:
    """
    Test that we can use custom arguments for the query function and that the
    typing with ParamSpec is working correctly.
    """

    class WordService:
        @tadl.query
        async def __query(
            self,
            criterion: Callable[[str], bool],
            *,
            language: Literal["en", "fr"] = "en",
        ) -> list[str]:
            words = (
                ["hello", "goodbye", "hotel"]
                if language == "en"
                else ["bonjour", "au revoir", "hôtel"]
            )
            return [word for word in words if criterion(word)]

        @__query.group_interface(
            key=lambda word: word[0],
            sort=lambda word: word,
        )
        async def for_english_first_letter(self, letters: list[str]) -> list[str]:
            """
            Load a list of words that start with the given first letter.
            """
            return await self.__query(lambda word: word[0] in letters)

        @__query.group_interface(
            key=lambda word: word[0],
            sort=lambda word: word,
        )
        async def for_french_first_letter(self, letters: list[str]) -> list[str]:
            """
            Load a list of words that start with the given first letter.
            """
            return await self.__query(lambda word: word[0] in letters, language="fr")

    w = WordService()
    assert await w.for_english_first_letter.load("h") == ["hello", "hotel"]
    assert await w.for_french_first_letter.load("b") == ["bonjour"]
    assert await w.for_french_first_letter.load("h") == ["hôtel"]
