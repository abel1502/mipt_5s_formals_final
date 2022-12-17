from __future__ import annotations
import typing
import dataclasses
import itertools
import functools
from functools import cached_property


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


class VGkBuilder(typing.Generic[T]):
    """
    A helper class to build $V_G^k$
    """
    
    _grammar: typing.Final[Grammar[T]]
    _k: typing.Final[int]
    _tables: UpdateableSet[FrozenTable[T]]
    _symbol_expansion_cache: typing.Dict[BaseSymbol, typing.Set[typing.Tuple[T, ...]]]
    
    def __init__(self, grammar: Grammar[T], k: int):
        grammar.new_start  # Trigger generation
        
        self._grammar = grammar
        self._k = k
        
        self._rules_by_lhs  # Trigger generation
        
        self._tables = UpdateableSet()
        
        self._symbol_expansion_cache = {}
    
    @cached_property
    def _rules_by_lhs(self) -> typing.Dict[Nonterminal, typing.List[Rule[T]]]:
        result: typing.Dict[Nonterminal, typing.List[Rule[T]]] = {}
        
        for rule in self._grammar.rules:
            result.setdefault(rule.lhs, []).append(rule)
        
        return result
    
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
            
            continuations: typing.Collection[typing.Tuple[T, ...]] = list(
                self.first_k(state.rule.rhs[state.rule_pos:], state.continuation)
            )
        
            # debug(">>", "continuations", continuations)
            
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
            
            next_item: Terminal[T]
            results.setdefault(next_item, Table()).add(state.shifted())
        
        return results
    
    def first_k(self, rule_symbols: typing.Sequence[BaseSymbol], continuation: typing.Tuple[T, ...]) -> typing.Generator[typing.Tuple[T, ...], None, None]:
        """
        Compute the first k tokens of the symbol sequence ending in the given continuation.
        """
        
        # debug(">>", "first_k", rule_symbols, continuation)
        
        for result in self._expand_sequence(rule_symbols):
            yield result + continuation[:self._k - len(result)]
    
    def _expand_sequence(self, rule_symbols: typing.Iterable[BaseSymbol]) -> typing.Set[typing.Tuple[T, ...]]:
        result: typing.Set[typing.Tuple[T, ...]] = set()
        cur_result: typing.Set[typing.Tuple[T, ...]] = {()}
        
        k: typing.Final[int] = self._k
        
        # debug(">>>", "expand_sequence", rule_symbols)
        
        for child_symbol in rule_symbols:
            cur_result = self._set_minkovsky_sum(
                cur_result,
                self._expand_symbol(child_symbol)
            )
            
            long_results = set(r for r in cur_result if len(r) >= k)
            
            result.update(r[:k] for r in long_results)
            cur_result.difference_update(long_results)
        
        result.update(r[:k] for r in cur_result)
        
        # debug(">>>", "expand_sequence result", result)
        
        return result
    
    def _expand_symbol(self, symbol: BaseSymbol) -> typing.Set[typing.Tuple[T, ...]]:
        """
        For each symbol, compute the set of all possible continuations of the symbol of length <=k.
        """
        
        # debug(">>>", "expand_symbol", symbol)
        
        if symbol not in self._symbol_expansion_cache:
            result: typing.Set[typing.Tuple[T, ...]] = self._do_expand_symbol(symbol, with_self=False)
            self._symbol_expansion_cache[symbol] = result
            
            while True:
                old_len = len(result)
                
                result.update(self._do_expand_symbol(symbol, with_self=True))
                
                if len(result) == old_len:
                    break
        
        # debug(">>>", "expand_symbol result", self._symbol_expansion_cache[symbol])
        
        return self._symbol_expansion_cache[symbol]
    
    def _do_expand_symbol(self, symbol: BaseSymbol, with_self: bool = False) -> typing.Set[typing.Tuple[T, ...]]:
        if symbol.is_terminal():
            symbol: Terminal[T]
            
            return {(symbol.get_token(),)}
        
        result: typing.Set[typing.Tuple[T, ...]] = set()
        
        for rule in self._rules_by_lhs.get(symbol, ()):
            if not with_self and symbol in rule.rhs:
                continue
            
            result.update(self._expand_sequence(rule.rhs))
        
        return result
    
    @staticmethod
    def _set_minkovsky_sum(set_a: typing.Set[T], set_b: typing.Set[T]) -> typing.Set[T]:
        """
        Compute the Minkovsky sum of the two sets.
        """
        
        return set(a + b for a, b in itertools.product(set_a, set_b))
    
    def build(self) -> typing.Tuple[FrozenTable[T], typing.Set[FrozenTable[T]]]:
        start_table: Table[T] = Table.initial(only(self._rules_by_lhs[self._grammar.new_start]))
        root: FrozenTable[T] = self._add_table(start_table)
        
        # debug(">", root)
        
        while self._tables.has_new():
            table: FrozenTable[T] = self._tables.process()
            
            for symbol, next_table in self._goto(table).items():
                table.gotos[symbol] = self._add_table(next_table)
        
        return root, set(self._tables)


# TODO: Constructors and error info...?
# TODO: Separate classes for shift-reduce and reduce-reduce conflicts?
class LRConflict(ParseError):
    pass


# This is probably overkill, but I at least like the way it has turned out.
@tagged_union
class Transition(typing.Generic[T]):
    shift: Unit
    reduce: Rule[T]
    accept: Unit


@dataclasses.dataclass(frozen=True)
class Action(typing.Generic[T]):
    target: LRState[T]


@dataclasses.dataclass()
class LRState(typing.Generic[T]):
    transitions: typing.Dict[typing.Tuple[T, ...], Transition[T]] = dataclasses.field(default_factory=dict)
    actions: typing.Dict[BaseSymbol | T, Action[T]] = dataclasses.field(default_factory=dict)


class LRTablesBuilder(typing.Generic[T]):
    _vgk_builder: VGkBuilder[T]
    _states: typing.Dict[FrozenTable[T], LRState[T]]
    
    def __init__(self, grammar: Grammar[T], k: int) -> None:
        self._vgk_builder = VGkBuilder(grammar, k)
        self._states = {}
    
    def _build_transitions(self, lr_state: LRState[T], vgk: FrozenTable[T]) -> None:
        transitions: typing.Dict[typing.Tuple[T, ...], Transition[T]] = lr_state.transitions
        assert not transitions, "Transitions already built"
        
        start_nonterm: Nonterminal[T] = self._vgk_builder._grammar.new_start
        
        for state in vgk.values:
            # Shift
            if state.rule_pos < len(state.rule):
                next_item: BaseSymbol = state.rule.rhs[state.rule_pos]
                
                if not next_item.is_terminal():
                    continue
                
                valid_continuations = self._vgk_builder.first_k(
                    state.rule.rhs[state.rule_pos:], state.continuation
                )
                
                for continuation in valid_continuations:
                    if continuation in transitions and not isinstance(transitions[continuation], Transition.shift):
                        raise LRConflict("Shift-reduce conflict")
                    
                    transitions[continuation] = Transition.shift()

                continue
            
            # Accept
            if state.rule.lhs == start_nonterm and not state.continuation:
                assert state.continuation not in transitions, "Accept conflicts should be impossible"
                
                transitions[state.continuation] = Transition.accept()

                continue
            
            # Reduce
            if state.continuation in transitions:
                raise LRConflict("{}-reduce conflict".format(
                    "Shift" if isinstance(transitions[state.continuation], Transition.shift) else "Reduce"
                ))
            
            transitions[state.continuation] = Transition.reduce(state.rule)
        
        return transitions
    
    def _state_for(self, vgk: FrozenTable[T]) -> LRState[T]:
        """
        Returns the state corresponding to a V_G^k. If the state does not exist, it is created.
        """
        
        if vgk not in self._states:
            lr_state = LRState()
            
            self._build_transitions(lr_state, vgk)
            
            self._states[vgk] = lr_state
        
        return self._states[vgk]
    
    def _process(self, vgk: FrozenTable[T]) -> LRState[T]:
        lr_state = self._state_for(vgk)
        
        for symbol, next_vgk in vgk.gotos.items():
            action = Action(self._process(next_vgk))
            lr_state.actions[symbol] = action
            
            if symbol.is_terminal():
                lr_state.actions[symbol.get_token()] = action
        
        return lr_state
    
    def build(self) -> LRState:
        return self._process(self._vgk_builder.build()[0])


__all__ = [
    # "State",
    # "Table",
    # "FrozenTable",
    # "VGkBuilder",
    "Transition",
    "Action",
    "LRState",
    "LRTablesBuilder",
]
