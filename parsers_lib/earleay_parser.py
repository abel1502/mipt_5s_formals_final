from __future__ import annotations
import typing
import io


from .peekable_stream import *
from .grammar import *
from .errors import ParseError
from .abstract_parser import Parser


class EarleyParser(Parser[bool]):
    _source: PeekableTextIO
    
    
    def __init__(self):
        pass
    
    def feed(self, source: str | io.TextIOBase) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        
        self._source = PeekableTextIO(source, limit=0, sentinel="\0")
    
    def parse(self) -> bool:
        raise NotImplementedError("Not implemented yet")


class EarleyParserBuilder:
    _grammar: Grammar
    
    
    def __init__(self, grammar: Grammar):
        self._grammar = grammar
    
    def build(self) -> EarleyParser:
        raise NotImplementedError("Not implemented yet")


__all__ = [
    "EarleyParser",
    "EarleyParserBuilder",
]
