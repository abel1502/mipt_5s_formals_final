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
    def feed(self, source: typing.Iterable[T]) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        ...

    @abc.abstractmethod
    def parse(self) -> R:
        ...


class ParserAPI(abc.ABC, typing.Generic[R, T]):
    """
    A class that provides a simple interface to a parser.
    """
    
    def __init__(self, grammar: Grammar[T], **kwargs):
        self._initialize(grammar, **kwargs)
    
    @abc.abstractmethod
    def _initialize(self, grammar: Grammar[T], **kwargs):
        """
        Override this method with the initialization code for the parser.
        The simplest example would be just saving the grammar.
        """
        ...
    
    @abc.abstractmethod
    def _get_parser(self, **kwargs) -> Parser[R, T]:
        """
        Override this method with the code to create a parser instance.
        """
        ...
    
    def parse(self, source: typing.Iterable[T], **kwargs) -> R:
        """
        Parse the given source and return the result.
        """
        
        parser: Parser[R, T] = self._get_parser(**kwargs)
        parser.feed(source)
        return parser.parse()


__all__ = [
    "Parser",
    "ParserAPI",
]
