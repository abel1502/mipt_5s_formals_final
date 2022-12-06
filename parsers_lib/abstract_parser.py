from __future__ import annotations
import typing
import io
import abc


from .grammar import *
from .abstract_tokenizer import *


T = typing.TypeVar("T", bound=Terminal)
R = typing.TypeVar("R")


class Parser(abc.ABC, typing.Generic[R, T]):
    """
    R is the return 
    """
    
    @abc.abstractmethod
    def feed(self, source: typing.Iterable[T], **kwargs) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        ...

    @abc.abstractmethod
    def parse(self) -> R:
        ...


def parse_with(parser: Parser[R, T], source: typing.Iterable[T], **kwargs) -> R:
    parser.feed(source, **kwargs)
    return parser.parse()


__all__ = [
    "Parser",
    "parse_with",
]
