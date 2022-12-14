from __future__ import annotations
import typing
import dataclasses
import itertools


from .grammar import *
from .errors import ParseError
from .abstract_parser import *
from .utils import *
from .tagged_union import *
from ._lr_parser_helpers import *


T = typing.TypeVar("T", bound=Terminal)


# This is probably overkill, but I at least like the way it has turned out.
@tagged_union
class Transition(typing.Generic[T]):
    shift: Unit
    reduce: Rule[T]
    accept: Unit


# Could actually introduce a separate builder, but screw it
class LRParserConfig(typing.Generic[T]):
    eof_token: T
    k: int
    transitions: typing.Dict[int, typing.Dict[T, Transition[T]]]
    actions: typing.Dict[int, typing.Dict[T, Transition[T]]]
    
    def __init__(self, grammar: Grammar[T], eof_token: T, k: int = 1):
        self.eof_token = eof_token
        self.k = k
        
        all_terms: typing.Set[T] = grammar.get_all_terminals()
        
        raise NotImplementedError()


class LRParser(Parser[bool, T], typing.Generic[T]):
    _config: LRParserConfig[T]
    _source: typing.Iterable[T]
    
    
    def __init__(self, config: LRParserConfig[T]):
        self._config = config
        
        raise NotImplementedError()
    
    def feed(self, source: typing.Iterable[T]) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        
        self._source = source
        
        raise NotImplementedError()
    
    def parse(self) -> bool:
        if not self._is_initialized():
            raise RuntimeError("Parser is not initialized")
        
        raise NotImplementedError()
        
        self._uninitialize()
        
        return result
    
    def _is_initialized(self) -> bool:
        return hasattr(self, "_source")
    
    def _uninitialize(self) -> None:
        del self._source


class LRParserAPI(ParserAPI[bool, T], typing.Generic[T]):
    _config: LRParserConfig[T]
    
    def _initialize(self, grammar: Grammar[T]):
        self._config = LRParserConfig(grammar)
    
    def _get_parser(self) -> LRParser[T]:
        return LRParser(self._config)


__all__ = [
    "LRParserConfig",
    "LRParser",
    "LRParserAPI"
]
