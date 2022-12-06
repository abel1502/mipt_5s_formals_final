from __future__ import annotations
import typing
import io
import abc


from .grammar import *


T = typing.TypeVar("T")


class Tokenizer(abc.ABC, typing.Generic[T]):
    @abc.abstractmethod
    def tokenize(self) -> typing.Iterable[T]:
        ...
    
    def __iter__(self) -> typing.Iterator[T]:
        return iter(self.tokenize())


__all__ = [
    "Tokenizer",
]
