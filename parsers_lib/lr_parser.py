from __future__ import annotations
import typing
import dataclasses
import itertools


from .grammar import *
from .errors import *
from .abstract_parser import *
from .peekable_stream import *
from .utils import *
from ._lr_parser_helpers import *


T = typing.TypeVar("T", bound=Terminal)


# Could actually introduce a separate builder, but screw it
class LRParserConfig(typing.Generic[T]):
    start_nonterm: Nonterminal
    eof_token: T
    k: int
    root_table: LRState[T]
    
    def __init__(self, grammar: Grammar[T], eof_token: T, k: int = 1):
        self.start_nonterm = grammar.new_start  # Also triggers its generation
        self.eof_token = eof_token
        self.k = k
        
        self.root_table = LRTablesBuilder(grammar, k).build()


class LRParser(Parser[bool, T], typing.Generic[T]):
    _config: LRParserConfig[T]
    _source: PeekableStream[T]
    # Could be a dataclass, but I'm too lazy for it at this point
    # TODO: Don't actually need to store symbols here...
    _stack: typing.List[typing.Tuple[BaseSymbol | T, LRState[T]]]
    
    
    def __init__(self, config: LRParserConfig[T]):
        self._config = config
    
    def feed(self, source: typing.Iterable[T]) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        
        self._source = PeekableStream(source, limit=self._config.k, sentinel=self._config.eof_token)
        self._stack = [(self._config.start_nonterm, self._config.root_table)]
    
    def parse(self) -> bool:
        if not self._is_initialized():
            raise RuntimeError("Parser is not initialized")
        
        result: bool = self._parse()
        
        self._uninitialize()
        
        return result
    
    def _is_initialized(self) -> bool:
        return hasattr(self, "_source")
    
    def _uninitialize(self) -> None:
        del self._source
    
    @property
    def _cur_state(self) -> LRState[T]:
        return self._stack[-1][1]
    
    def _parse(self) -> bool:
        # For faster access
        k: typing.Final[int] = self._config.k
        source: PeekableStream[T] = self._source
        stack: typing.List[typing.Tuple[BaseSymbol | T, LRState[T]]] = self._stack
        
        while stack:
            cur_state: LRState[T] = self._cur_state
            
            preview: typing.List[T] = source.peek(k)
            
            if preview not in cur_state.transitions:
                return False
            
            transition: Transition[T] = cur_state.transitions[preview]
            
            if isinstance(transition, Transition.accept):
                return True
            
            new_state: LRState[T] = cur_state.actions[transition.symbol]
            
            if isinstance(transition, Transition.shift):
                stack.append((source.peek1(), new_state))
                source.next()
                continue
            
            assert isinstance(transition, Transition.reduce)
            rule: Rule[T] = transition.value
            
            for i in range(len(rule)):
                stack.pop()
            
            stack.append((rule.lhs, self._cur_state.actions[rule.lhs]))
        
        assert False, "Shouldn't be reachable"


class LRParserAPI(ParserAPI[bool, T], typing.Generic[T]):
    _config: LRParserConfig[T]
    
    def __init__(self, grammar: Grammar[T], eof_token: T, k: int = 1):
        self._config = LRParserConfig(grammar, eof_token, k)
    
    def _get_parser(self) -> LRParser[T]:
        return LRParser(self._config)


__all__ = [
    "LRParserConfig",
    "LRParser",
    "LRParserAPI"
]
