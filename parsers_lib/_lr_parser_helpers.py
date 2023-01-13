from __future__ import annotations
import typing
import dataclasses
import itertools
import functools
from functools import cached_property
from contextlib import contextmanager


from .grammar import *
from .utils import *
from .errors import *
from .tagged_union import *


T = typing.TypeVar("T", bound=Terminal)


# TODO: Confusing names, maybe rename
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
        return Table(new_values={State(start_rule)})
    
    def freeze(self) -> FrozenTable[T]:
        assert not self.has_new(), "Table not yet complete"
        
        return FrozenTable(frozenset(self.values))


@dataclasses.dataclass(frozen=True)
class FrozenTable(typing.Generic[T]):
    values: typing.FrozenSet[State[T]]
    gotos: typing.Dict[BaseSymbol, FrozenTable[T]] = dataclasses.field(hash=False, compare=False, default_factory=dict)


class FirstKProvider(typing.Generic[T]):
    _grammar: typing.Final[Grammar[T]]
    _k: typing.Final[int]
    _symbol_expansion_cache: typing.Dict[BaseSymbol, typing.Set[typing.Tuple[T, ...]]]
    
    def __init__(self, grammar: Grammar[T], k: int):
        grammar.new_start  # Trigger generation
        
        self._grammar = grammar
        self._k = k
        
        self.rules_by_lhs  # Trigger generation
        
        self._symbol_expansion_cache = {}
        
        self._prepare()
    
    @cached_property
    def rules_by_lhs(self) -> typing.Dict[Nonterminal, typing.List[Rule[T]]]:
        result: typing.Dict[Nonterminal, typing.List[Rule[T]]] = {}
        
        for rule in self._grammar.rules:
            result.setdefault(rule.lhs, []).append(rule)
        
        return result
    
    @property
    def new_start(self) -> Nonterminal[T]:
        return self._grammar.new_start
    
    @property
    def new_start_rule(self) -> Rule[T]:
        return only(self.rules_by_lhs[self.new_start])
    
    @staticmethod
    def _set_minkovsky_sum(set_a: typing.Set[T], set_b: typing.Set[T]) -> typing.Set[T]:
        """
        Compute the Minkovsky sum of the two sets.
        """
        
        return set(a + b for a, b in itertools.product(set_a, set_b))
    
    @cached_property
    def _sufficient_repetitions(self) -> int:
        return self._k * len(self._grammar.rules)
    
    def _prepare(self) -> None:
        nonterminals = list(self._grammar.nonterminals.values())
        
        for _ in range(self._sufficient_repetitions):
            for symbol in nonterminals:
                self._expand_symbol(symbol, explicit=True)
    
    def _expand_sequence(self, rule_symbols: typing.Iterable[BaseSymbol]) -> typing.Set[typing.Tuple[T, ...]]:
        result: typing.Set[typing.Tuple[T, ...]] = set()
        cur_result: typing.Set[typing.Tuple[T, ...]] = {()}
        
        k = self._k
        
        # debug(">>>", "expand_sequence", rule_symbols)
        
        for child_symbol in rule_symbols:
            cur_result = self._set_minkovsky_sum(cur_result, self._expand_symbol(child_symbol))
            
            long_results = set(r for r in cur_result if len(r) >= k)
            
            result.update(r[:k] for r in long_results)
            cur_result.difference_update(long_results)
        
        result.update(r[:k] for r in cur_result)
        
        # debug(">>>", "expand_sequence result", result)
        
        return result
    
    def _expand_symbol(self, symbol: BaseSymbol, explicit: bool = False) -> typing.Set[typing.Tuple[T, ...]]:
        """
        For each symbol, compute the set of all possible continuations of the symbol of length <=k.
        """
        
        # debug(">>>", f"expand_symbol({symbol})")
        
        if symbol not in self._symbol_expansion_cache or explicit:
            result: typing.Set[typing.Tuple[T, ...]] = \
                self._symbol_expansion_cache.setdefault(symbol, set())
            
            for _ in range(self._sufficient_repetitions):
                result.update(self._do_expand_symbol(symbol))
        
            # debug(">>>", f"expand_symbol({symbol}) result", result)
        
        return self._symbol_expansion_cache[symbol]
    
    def _do_expand_symbol(self, symbol: BaseSymbol) -> typing.Set[typing.Tuple[T, ...]]:
        if symbol.is_terminal():
            symbol: Terminal[T]
            
            return {(symbol.get_token(),)}
        
        result: typing.Set[typing.Tuple[T, ...]] = set()
        
        for rule in self.rules_by_lhs.get(symbol, ()):
            result.update(self._expand_sequence(rule.rhs))
        
        return result

    def first_k(self, rule_symbols: typing.Sequence[BaseSymbol], continuation: typing.Tuple[T, ...]) -> typing.Set[typing.Tuple[T, ...]]:
        """
        Compute the first k tokens of the symbol sequence ending in the given continuation.
        """
        
        # debug(">>", "first_k", rule_symbols, continuation)
        
        result = self._expand_sequence(rule_symbols)
        
        k = self._k
        result = set(r + continuation[:k - len(r)] for r in result)
        
        return result


class VGkBuilder(typing.Generic[T]):
    """
    A helper class to build $V_G^k$
    """
    
    _first_k_provider: FirstKProvider[T]
    _tables: UpdateableSet[FrozenTable[T]]
    
    def __init__(self, grammar: Grammar[T], k: int):
        self._first_k_provider = FirstKProvider(grammar, k)
        
        self._tables = UpdateableSet()
    
    def _add_table(self, table: Table[T]) -> FrozenTable[T]:
        """
        Add the closure of the given table to the registry, if it hasn't been seen yet
        """
        
        self._complete_table(table)
        
        frozen_table: FrozenTable[T] = table.freeze()
        
        if frozen_table not in self._tables:
            self._tables.add(frozen_table)
        
        return frozen_table
    
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
        
            # debug(">>", "querying", state.rule.rhs[state.rule_pos + 1:], state.continuation)
            
            continuations: typing.Collection[typing.Tuple[T, ...]] = list(
                self._first_k(state.rule.rhs[state.rule_pos + 1:], state.continuation)
            )
        
            # debug(">>>", "continuations", continuations)
            
            for rule in self._rules_by_lhs.get(next_item, ()):
                for continuation in continuations:
                    table.add(State(rule, continuation=continuation))

    def _goto(self, table: FrozenTable[T]) -> typing.Mapping[BaseSymbol, Table[T]]:
        """
        Apply the goto operation to the given table, and return the result.
        """
        
        results: typing.Dict[BaseSymbol, Table[T]] = {}
        
        for state in table.values:
            next_item: BaseSymbol | None = state.get_next_item()
            
            if next_item is None:
                continue
            
            results.setdefault(next_item, Table()).add(state.shifted())
        
        return results
    
    def _first_k(self, rule_symbols: typing.Sequence[BaseSymbol], continuation: typing.Tuple[T, ...]) -> typing.Generator[typing.Tuple[T, ...], None, None]:
        return self._first_k_provider.first_k(rule_symbols, continuation)
    
    @property
    def _rules_by_lhs(self) -> typing.Mapping[Nonterminal, typing.Collection[Rule[T]]]:
        return self._first_k_provider.rules_by_lhs
    
    def build(self) -> typing.Tuple[FrozenTable[T], typing.Set[FrozenTable[T]]]:
        start_table: Table[T] = Table.initial(self._first_k_provider.new_start_rule)
        root: FrozenTable[T] = self._add_table(start_table)
        
        while self._tables.has_new():
            table: FrozenTable[T] = self._tables.process()
            
            for symbol, next_table in self._goto(table).items():
                table.gotos[symbol] = self._add_table(next_table)
        
        # debug(">", root)
        
        return root, set(self._tables)
    
    @property
    def first_k_provider(self) -> FirstKProvider[T]:
        return self._first_k_provider


# TODO: Constructors and error info...?
# TODO: Separate classes for shift-reduce and reduce-reduce conflicts?
class LRConflict(ParseError):
    pass


# This is probably overkill, but I at least like the way it has turned out.
@tagged_union
class Action(typing.Generic[T]):
    shift: Unit
    reduce: Rule[T]
    accept: Unit


@dataclasses.dataclass(frozen=True)
class Transition(typing.Generic[T]):
    target: LRState[T]


@dataclasses.dataclass()
class LRState(typing.Generic[T]):
    actions: typing.Dict[typing.Tuple[T, ...], Action[T]] = dataclasses.field(default_factory=dict)
    transitions: typing.Dict[BaseSymbol | T, Transition[T]] = dataclasses.field(default_factory=dict)


class LRTablesBuilder(typing.Generic[T]):
    _vgk_builder: VGkBuilder[T]
    _states: typing.Dict[FrozenTable[T], LRState[T]]
    
    def __init__(self, grammar: Grammar[T], k: int) -> None:
        self._vgk_builder = VGkBuilder(grammar, k)
        self._states = {}
    
    def _build_actions(self, lr_state: LRState[T], vgk: FrozenTable[T]) -> None:
        actions: typing.Dict[typing.Tuple[T, ...], Action[T]] = lr_state.actions
        assert not actions, "Transitions already built"
        
        first_k_provider = self._vgk_builder.first_k_provider
        
        for state in vgk.values:
            # Shift
            if state.rule_pos < len(state.rule):
                next_item: BaseSymbol = state.rule.rhs[state.rule_pos]
                
                if not next_item.is_terminal():
                    continue
                
                valid_continuations = first_k_provider.first_k(
                    state.rule.rhs[state.rule_pos:], state.continuation
                )
                
                for continuation in valid_continuations:
                    if continuation in actions and not isinstance(actions[continuation], Action.shift):
                        raise LRConflict("Shift-reduce conflict")
                    
                    actions[continuation] = Action.shift()

                continue
            
            # Accept
            if state.rule.lhs == first_k_provider.new_start and not state.continuation:
                assert state.continuation not in actions, "Accept conflicts should be impossible"
                
                actions[state.continuation] = Action.accept()

                continue
            
            # Reduce
            if state.continuation in actions:
                raise LRConflict("{}-reduce conflict".format(
                    "Shift" if isinstance(actions[state.continuation], Action.shift) else "Reduce"
                ))
            
            actions[state.continuation] = Action.reduce(state.rule)
    
    def _state_for(self, vgk: FrozenTable[T]) -> LRState[T]:
        """
        Returns the state corresponding to a V_G^k. If the state does not exist, it is created.
        """
        
        if vgk not in self._states:
            lr_state = LRState()
            
            self._build_actions(lr_state, vgk)
            
            self._states[vgk] = lr_state
        
        return self._states[vgk]
    
    def _process(self, vgk: FrozenTable[T]) -> LRState[T]:
        lr_state = self._state_for(vgk)
        
        for symbol, next_vgk in vgk.gotos.items():
            transition = Transition(self._process(next_vgk))
            
            lr_state.transitions[symbol] = transition
            
            if symbol.is_terminal():
                # A bit hacky, but whatever...
                lr_state.transitions[symbol.get_token()] = transition
        
        return lr_state
    
    def build(self) -> LRState:
        return self._process(self._vgk_builder.build()[0])


__all__ = [
    # "State",
    # "Table",
    # "FrozenTable",
    # "VGkBuilder",
    "Action",
    "Transition",
    "LRState",
    "LRTablesBuilder",
]
