from __future__ import annotations
import typing
# import functools
import itertools
import dataclasses


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


# def compare_iterables(*iterables: typing.Iterable[T]) -> bool:
#     """
#     Returns True if all iterables are equal, False otherwise
#     """
    
#     for values in itertools.zip_longest(*iterables, fillvalue=object()):
#         if not all(value == values[0] for value in values[1:]):
#             return False
    
#     return True


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


@dataclasses.dataclass(frozen=True)
class UpdateableSet(typing.Generic[T]):
    values: typing.Set[T] = dataclasses.field(default_factory=set)
    new_values: typing.Set[T] = dataclasses.field(default_factory=set)
    
    def add(self, value: T) -> None:
        if value not in self.values:
            self.new_values.add(value)
    
    def has_new(self) -> bool:
        return bool(self.new_values)
    
    def process(self) -> T:
        state = self.new_values.pop()
        
        self.values.add(state)
        
        return state
    
    def refresh_all(self) -> None:
        self.new_values.update(self.values)
        self.values.clear()
    
    def __iter__(self) -> typing.Iterator[T]:
        return itertools.chain(self.values, self.new_values)
    
    def __len__(self) -> int:
        return len(self.values) + len(self.new_values)


def debug(*args) -> None:
    """
    A convenience function to encapsulate debug printing.
    
    Disabling is currently done by inserting a short-circuit `return` :)
    """
    
    # return
    
    print(*args, flush=True)


__all__ = [
    "only",
    # "compare_iterables",
    # "VirtualMapping",
    "UpdateableSet",
    "debug",
]
