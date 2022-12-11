from __future__ import annotations
import typing
import dataclasses
import itertools


from .grammar import *
from .errors import ParseError
from .abstract_parser import *
from .utils import *


T = typing.TypeVar("T", bound=Terminal)


@dataclasses.dataclass(frozen=True)
class State(typing.Generic[T]):
    rule: Rule[T]
    rule_pos: int = 0
    start_offset: int = 0
    
    def get_next_item(self) -> BaseSymbol | None:
        if self.rule_pos == len(self.rule):
            return None
        
        return self.rule.rhs[self.rule_pos]
    
    def shifted(self) -> State[T]:
        if self.rule_pos == len(self.rule):
           raise ValueError("Cannot shift a completed state")
        
        return dataclasses.replace(self, rule_pos=self.rule_pos + 1)


@dataclasses.dataclass(frozen=True)
class Table(typing.Generic[T]):
    states: typing.Set[State[T]] = dataclasses.field(default_factory=set)
    new_states: typing.Set[State[T]] = dataclasses.field(default_factory=set)
    
    @staticmethod
    def initial(start_rule: Rule[T]) -> Table:
        return Table(new_states={State(start_rule)})
    
    def add_state(self, state: State[T]) -> None:
        if state not in self.states:
            self.new_states.add(state)
    
    def has_new_states(self) -> bool:
        return bool(self.new_states)
    
    def process_state(self) -> State[T]:
        state = self.new_states.pop()
        
        self.states.add(state)
        
        return state
    
    def is_successful(self, start_rule: Rule[T]) -> bool:
        return any(
            state.rule == start_rule and state.rule_pos == len(state.rule)
            for state in self.states
        )
    
    def __iter__(self) -> typing.Iterator[State]:
        return itertools.chain(self.states, self.new_states)


class EarleyParserConfig(typing.Generic[T]):
    start_rule: Rule[T]
    rules_by_lhs: typing.Dict[Nonterminal, typing.List[Rule[T]]]
    
    def __init__(self, grammar: Grammar[T]):
        grammar = grammar.split_long_terminals()
        
        self.start_rule = only(grammar.get_rules_by_lhs(grammar.new_start))
        self.rules_by_lhs = {}
        
        self._populate_rules_by_lhs(grammar)
    
    def _populate_rules_by_lhs(self, grammar: Grammar[T]):
        for rule in grammar.rules:
            self.rules_by_lhs.setdefault(rule.lhs, []).append(rule)


class EarleyParser(Parser[bool, T], typing.Generic[T]):
    _config: EarleyParserConfig[T]
    _source: typing.Iterable[T]
    _tables: typing.List[Table[T]]
    
    
    def __init__(self, config: EarleyParserConfig[T]):
        self._config = config
    
    def feed(self, source: typing.Iterable[T]) -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        
        self._source = source
        self._tables = [Table.initial(self._config.start_rule)]
    
    def parse(self) -> bool:
        if not self._is_initialized():
            raise RuntimeError("Parser is not initialized")
        
        for tok in self._source:
            self._step(tok)
        
        self._step(None)
        
        result: bool = self._cur_table.is_successful(self._config.start_rule)
        
        self._uninitialize()
        
        return result
    
    def _is_initialized(self) -> bool:
        return hasattr(self, "_source")
    
    def _uninitialize(self) -> None:
        del self._source
    
    @property
    def _cur_table(self) -> Table[T]:
        return self._tables[-2]
    
    @property
    def _next_table(self) -> Table[T]:
        return self._tables[-1]
    
    @property
    def _cur_idx(self) -> int:
        return len(self._tables) - 2
    
    def _step(self, tok: T | None) -> None:
        self._tables.append(Table())
        
        table: typing.Final[Table[T]] = self._cur_table
        while table.has_new_states():
            state: State = table.process_state()
            
            next_item: BaseSymbol | None = state.get_next_item()
            
            if next_item is None:
                self._complete(state)
            elif next_item.isTerminal():
                self._scan(state, next_item, tok)
            else:
                self._predict(next_item)
    
    def _scan(self, state: State, terminal: Terminal[T], tok: T | None) -> None:
        if tok is None:
            return
        
        if terminal.matches(tok):
            self._next_table.add_state(state.shifted())
    
    def _predict(self, nonterminal: Nonterminal) -> None:
        for rule in self._config.rules_by_lhs[nonterminal]:
            self._cur_table.add_state(State(rule, start_offset=self._cur_idx))
    
    def _complete(self, state: State) -> None:
        for prev_state in list(self._tables[state.start_offset]):
            next_item: BaseSymbol | None = prev_state.get_next_item()
            
            if next_item != state.rule.lhs:
                continue
            
            self._cur_table.add_state(prev_state.shifted())


class EarleyParserAPI(ParserAPI[bool, T], typing.Generic[T]):
    _config: EarleyParserConfig[T]
    
    def _initialize(self, grammar: Grammar[T]):
        self._config = EarleyParserConfig(grammar)
    
    def _get_parser(self) -> EarleyParser[T]:
        return EarleyParser(self._config)
    


__all__ = [
    "EarleyParserConfig",
    "EarleyParser",
    "EarleyParserAPI"
]
