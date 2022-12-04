from __future__ import annotations
import typing
import functools
import itertools


T = typing.TypeVar("T")
K = typing.TypeVar("K")


def only(iterable: typing.Iterable[T]) -> T:
    """
    Returns the only element of the iterable, or raises ValueError if there's more than one
    """
    
    iterator = iter(iterable)
    
    try:
        value = next(iterator)
    except StopIteration:
        raise ValueError("Expected exactly one element, but got none")
    
    try:
        next(iterator)
    except StopIteration:
        return value
    
    raise ValueError("Expected exactly one element, but got more")


# class VirtualMapping(typing.Generic[T, K], typing.Mapping[K, T]):
#     def __init__(self, generator: typing.Callable[[T], K]):
#         self.generator = generator
#     
#     def __getitem__(self, key: K) -> T:
#         return self.generator(key)
#     
#     def __iter__(self) -> typing.Iterator[K]:
#         raise NotImplementedError("Cannot iterate over a virtual mapping")
#     
#     def __len__(self) -> int:
#         raise NotImplementedError("Virtual mappings have no determined length")


__all__ = [
    "only",
    # "VirtualMapping",
]
