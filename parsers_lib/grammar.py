from __future__ import annotations
import typing
import dataclasses
import abc
from functools import cached_property

from .utils import *


class BaseSymbol(abc.ABC):
    @abc.abstractmethod
    def isTerminal() -> bool:
        ...


@dataclasses.dataclass(frozen=True, repr=False)
class Nonterminal(BaseSymbol):
    name: str
    
    def isTerminal(self) -> bool:
        return False
    
    def __repr__(self):
        return self.name


@dataclasses.dataclass(frozen=True, repr=False)
class Terminal(BaseSymbol):
    value: str
    
    def isTerminal(self) -> bool:
        return True
    
    def __repr__(self):
        return repr(self.value)


@dataclasses.dataclass(frozen=True, repr=False)
class Rule:
    lhs: Nonterminal
    rhs: typing.Collection[BaseSymbol] = dataclasses.field(default_factory=tuple)
    
    def __init__(self, lhs: Nonterminal, rhs: typing.Collection[BaseSymbol] = ()):
        object.__setattr__(self, "lhs", lhs)
        object.__setattr__(self, "rhs", tuple(rhs))
    
    def __len__(self):
        return len(self._rules)
    
    def get_nonterminals(self) -> typing.Generator[Nonterminal, None, None]:
        yield self.lhs
        
        for symbol in self.rhs:
            if isinstance(symbol, Nonterminal):
                yield symbol
    
    def __repr__(self):
        return f"<{self.lhs} -> {' '.join(map(str, self.rhs))}>"


class Grammar:
    _rules: typing.Final[typing.Set[Rule]]
    _nonterminals: typing.Final[typing.Dict[str, Nonterminal]]
    _start: typing.Final[str | Nonterminal]
    
    def __init__(self, rules: typing.Iterable[Rule] = (), start: str | Nonterminal = "S"):
        self._rules = set(rules)
        self._nonterminals = {rule.lhs.name: rule.lhs for rule in self._rules}
        
        self._start = start
    
    @cached_property
    def rules(self) -> typing.Collection[Rule]:
        return self._rules
    
    @cached_property
    def nonterminals(self) -> typing.Mapping[str, Nonterminal]:
        return self._nonterminals
    
    @cached_property
    def start(self) -> Nonterminal:
        return self.resolve_nonterminal(self._start)
    
    @cached_property
    def new_start(self) -> Nonterminal:
        value = Nonterminal(f"_new_start")
        
        assert not self.has_nonterminal(value)
        
        self.add_rule(Rule(value, [self.start]))
    
    def has_nonterminal(self, nonterm: str | Nonterminal) -> bool:
        if isinstance(nonterm, Nonterminal):
            return nonterm in self.nonterminals.values()
        
        return nonterm in self.nonterminals.keys()
    
    def resolve_nonterminal(self, nonterm: str | Nonterminal) -> Nonterminal:
        if not self.has_nonterminal(nonterm):
            raise KeyError(f"Nonterminal {nonterm} not found in grammar")
        
        if isinstance(nonterm, str):
            nonterm: Nonterminal = self.nonterminals[nonterm]
        
        return nonterm
    
    def add_nonterminal(self, nonterm: Nonterminal | str) -> Nonterminal:
        if isinstance(nonterm, str):
            nonterm = Nonterminal(nonterm)
        
        if self.has_nonterminal(nonterm.name):
            raise KeyError(f"Duplicate nonterminal name: {nonterm.name}")
        
        self._nonterminals[nonterm.name] = nonterm

    def ensure_nonterminal(self, nonterm: str | Nonterminal) -> Nonterminal:
        if isinstance(nonterm, str):
            nonterm = Nonterminal(nonterm)
        
        if not self.has_nonterminal(nonterm):
            self.add_nonterminal(nonterm)
        
        return nonterm
    
    def add_rule(self, rule: Rule) -> None:
        for nonterm in rule.get_nonterminals():
            self.ensure_nonterminal(nonterm)
        
        self._rules.add(rule)
    
    def create_rule(self, lhs: str | Nonterminal, rhs: typing.Iterable[str | Nonterminal]) -> None:
        self.add_rule(Rule(lhs, tuple(rhs)))
    
    def get_rules_by_lhs(self, lhs: Nonterminal) -> typing.Iterable[Rule]:
        return filter(lambda rule: rule.lhs == lhs, self._rules)
    
    def prune(self) -> None:
        self._prune_unused_nonterminals()
    
    def _prune_unused_nonterminals(self) -> None:
        # Trigger it here just to make sure it's already created
        self.new_start
        
        used_nonterminals = set(rule.lhs for rule in self._rules)
        used_nonterminals.add(self.new_start)  # It's considered used in any case
        # used_nonterminals.add(self.start)  # Unnecessary, since it's always used by the new start rule
        
        self._nonterminals -= used_nonterminals
    
    def __repr__(self):
        return f"Grammar({', '.join(map(repr, self._rules))})"


__all__ = [
    "BaseSymbol",
    "Nonterminal",
    "Terminal",
    "Rule",
    "Grammar",
]
