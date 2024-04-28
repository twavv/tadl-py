from __future__ import annotations

from typing import Callable, Awaitable, Sequence

from tadl.types import TKey, TElt, Scalar

# A function that loads a batch of values for the given keys.
# The returned list **MUST** have the same length as the input list of keys and
# be in the same order.
LoadFn = Callable[[list[TKey]], Awaitable[list[TElt]]]


def match_array(
    keys: Sequence[TKey],
    values: Sequence[TElt],
    key: Callable[[TElt], TKey],
) -> list[TElt | None]:
    """
    Match the values to the keys in the order of the keys.

    If a value is not found for a key, None is returned in its place.

    # Example
    ```python
    keys = [1, 2, 3]
    values = [6, 4]
    match_array(keys, values, key=lambda x: x/2)
    # Output: [None, 4, 6]
    ```
    """
    items = {key(value): value for value in values}
    return [items.get(key) for key in keys]


def group_array(
    keys: Sequence[TKey],
    values: Sequence[TElt],
    *,
    key: Callable[[TElt], TKey],
    sort: Callable[[TElt], Scalar],
) -> list[list[TElt]]:
    """
    Group the values by the keys into an array of arrays in the same order as
    the input keys array.

    The values are sorted within each group by the sort function for
    deterministic ordering.

    # Example
    ```python
    keys = [1, 2, 3, 4]
    values = [(1, "one"), (2, "two"), (1, "uno"), (2, "dos"), (3, "three")]
    group_array(
        keys,
        values,
        key=lambda x: x[0],
        sort=lambda x: x[1],
    )
    # Output: [[(1, "one"), (1, "uno")], [(2, "dos"), (2, "two")], [(3, "three")], []]
    ```
    """
    groups: dict[TKey, list[TElt]] = {}
    for value in values:
        group = groups.setdefault(key(value), [])
        group.append(value)
    for group in groups.values():
        group.sort(key=sort)
    return [groups.get(key) or [] for key in keys]
