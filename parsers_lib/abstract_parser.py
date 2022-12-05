from __future__ import annotations
import typing
import io
import abc


T = typing.TypeVar("T")


class Parser(abc.ABC, typing.Generic[T]):
    @abc.abstractmethod
    def feed(self, source: str | io.TextIOBase, **kwargs) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        ...

    @abc.abstractmethod
    def parse(self) -> T:
        ...


def parse_with(parser: Parser[T], source: str | io.TextIOBase, **kwargs) -> T:
    parser.feed(source, **kwargs)
    return parser.parse()


__all__ = [
    "Parser",
    "parse_with",
]
