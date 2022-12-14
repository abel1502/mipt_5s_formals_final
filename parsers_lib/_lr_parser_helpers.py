from __future__ import annotations
import typing
import dataclasses
import itertools
import functools
from functools import cached_property


from .grammar import *
from .utils import *


T = typing.TypeVar("T", bound=Terminal)


@dataclasses.dataclass(frozen=True)
class State(typing.Generic[T]):
    rule: Rule[T]
    rule_pos: int = 0
    continuation: typing.Tuple[T, ...] = ()
    
    def get_next_item(self) -> BaseSymbol | None:
        if self.rule_pos == len(self.rule):
            return None
        
        return self.rule.rhs[self.rule_pos]
    
    def shifted(self) -> State[T]:
        if self.rule_pos == len(self.rule):
           raise ValueError("Cannot shift a completed state")
        
        return dataclasses.replace(self, rule_pos=self.rule_pos + 1)


class Table(UpdateableSet[State[T]], typing.Generic[T]):
    @staticmethod
    def initial(start_rule: Rule[T]) -> Table:
        return Table(new_states={State(start_rule)})
    
    def freeze(self, key: typing.Tuple[T, ...]) -> FrozenTable[T]:
        assert not self.has_new(), "Table not yet complete"
        
        return FrozenTable(self, key)


@dataclasses.dataclass(frozen=True)
class FrozenTable(typing.Generic[T]):
    values: typing.FrozenSet[State[T]]
    key: typing.Tuple[T, ...] = dataclasses.field(hash=False, compare=False)


class VGkBuilder(typing.Generic[T]):
    """
    A helper class to build $V_G^k$
    """
    
    _grammar: typing.Final[Grammar[T]]
    _k: typing.Final[int]
    _tables: UpdateableSet[FrozenTable[T]]
    
    def __init__(self, grammar: Grammar[T], k: int):
        grammar.new_start  # Trigger generation
        
        self._grammar = grammar
        self._k = k
        
        self._rules_by_lhs  # Trigger generation
        
        self._tables = UpdateableSet()
        
        self._first_k_cache = {}
    
    @cached_property
    def _rules_by_lhs(self) -> typing.Dict[Nonterminal, typing.List[Rule[T]]]:
        result: typing.Dict[Nonterminal, typing.List[Rule[T]]] = {}
        
        for rule in self._grammar.rules:
            result.setdefault(rule.lhs, []).append(rule)
        
        return result
    
    def _add_table(self, key: typing.Tuple[T, ...], table: Table[T]) -> None:
        """
        Add the closure of the given table to the registry, if it hasn't been seen yet
        """
        
        assert key not in self._tables
        
        self._complete_table(table)
        
        frozen_table: FrozenTable[T] = table.freeze(key)
        
        if frozen_table not in self._tables:
            self._tables.add(frozen_table)
    
    def _complete_table(self, table: Table[T]) -> None:
        """
        Apply the closure operation to the given table.
        """
        
        while table.has_new():
            state = table.process()
            next_item: BaseSymbol | None =  state.get_next_item()
            
            if next_item is None or next_item.is_terminal():
                continue
            
            next_item: Nonterminal
            
            continuations: typing.Collection[typing.Tuple[T, ...]] = list(
                self._first_k(state.rule.rhs[state.rule_pos:], state.continuation)
            )
            
            for rule in self._rules_by_lhs.get(next_item, ()):
                for continuation in continuations:
                    table.add(State(rule, continuation=continuation))

    def _goto(self, table: FrozenTable[T]) -> typing.Mapping[T, Table[T]]:
        """
        Apply the goto operation to the given table, and return the result.
        """
        
        results: typing.Dict[T, Table[T]] = {}
        
        for state in table.values:
            next_item: BaseSymbol | None = state.get_next_item()
            
            if next_item is None or not next_item.is_terminal():
                continue
            
            next_item: Terminal[T]
            results.setdefault(next_item.get_token(), Table()).add(state.shifted())
        
        return results
    
    def _first_k(self, rule_symbols: typing.Sequence[BaseSymbol], continuation: typing.Tuple[T, ...]) -> typing.Generator[typing.Tuple[T, ...], ...]:
        """
        Compute the first k tokens of the symbol sequence ending in the given continuation.
        """
        
        results: typing.Set[typing.Tuple[T, ...]] = set(
            self._expand_sequence(tuple(rule_symbols))
        )
        
        for result in results:
            yield result + continuation[:self._k - len(result)]
    
    def _expand_sequence(self, rule_symbols: typing.Iterable[BaseSymbol]) -> typing.FrozenSet[typing.Tuple[T, ...]]:
        result: typing.Set[typing.Tuple[T, ...]] = set()
        cur_result: typing.Set[typing.Tuple[T, ...]] = set()
        
        k: typing.Final[int] = self._k
        
        for child_symbol in rule_symbols:
            cur_result = self._set_minkovsky_sum(
                cur_result,
                self._expand_symbol(child_symbol)
            )
            
            long_results = set(r for r in cur_result if len(r) >= k)
            
            result.update(r[:k] for r in long_results)
            cur_result.difference_update(long_results)
        
        return frozenset(result)
    
    @functools.cache
    def _expand_symbol(self, symbol: BaseSymbol) -> typing.FrozenSet[typing.Tuple[T, ...]]:
        """
        For each symbol, compute the set of all possible continuations of the symbol of length <=k.
        """
        
        if symbol.is_terminal():
            symbol: Terminal[T]
            
            return frozenset({(symbol.get_token(),)})
        
        result: typing.Set[typing.Tuple[T, ...]] = set()
        
        for rule in self._rules_by_lhs.get(symbol, ()):
            result.update(self._expand_sequence(rule.rhs))
        
        return frozenset(result)
    
    @staticmethod
    def _set_minkovsky_sum(set_a: typing.Set[T], set_b: typing.Set[T]) -> typing.Set[T]:
        """
        Compute the Minkovsky sum of the two sets.
        """
        
        return set(a + b for a, b in itertools.product(set_a, set_b))
    
    def build(self) -> typing.Collection[FrozenTable[T]]:
        start_table: Table[T] = Table.initial(only(self._rules_by_lhs[self._grammar.new_start]))
        self._add_table((), start_table)
        
        while self._tables.has_new():
            table: FrozenTable[T] = self._tables.process()
            
            for token, next_table in self._goto(table).items():
                self._add_table(table.key + (token,), next_table)
        
        return set(self._tables)

__all__ = [
    "State",
    "VGkBuilder",
]
