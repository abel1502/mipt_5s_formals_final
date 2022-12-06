from __future__ import annotations
import typing
import dataclasses
import abc
from functools import cached_property

from .utils import *


T = typing.TypeVar("T")


class BaseSymbol(abc.ABC):
    """
    Base class for all symbols in a grammar
    """
    
    @abc.abstractmethod
    def isTerminal() -> bool:
        ...


class Terminal(BaseSymbol, typing.Generic[T]):
    """
    Base class for all terminals.
    
    Provided for extensibility.
    """
    
    def isTerminal(self) -> bool:
        return True
    
    @abc.abstractmethod
    def matches(self, token: T) -> bool:
        """
        Returns whether the given token matches this terminal.
        """

        ...


@dataclasses.dataclass(frozen=True, repr=False)
class Nonterminal(BaseSymbol):
    name: str
    
    def isTerminal(self) -> bool:
        return False
    
    def __repr__(self):
        return self.name


@dataclasses.dataclass(frozen=True, repr=False)
class StrTerminal(Terminal[str]):
    value: str
    
    def matches(self, token: str) -> bool:
        return self.value == token
    
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
            if not symbol.isTerminal():
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
    
    @property
    def rules(self) -> typing.Collection[Rule]:
        return self._rules
    
    @property
    def nonterminals(self) -> typing.Mapping[str, Nonterminal]:
        return self._nonterminals
    
    @cached_property
    def start(self) -> Nonterminal:
        return self.resolve_nonterminal(self._start)
    
    @cached_property
    def new_start(self) -> Nonterminal:
        value = Nonterminal(f"__new_start__")
        
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
    
    def split_long_terminals(self) -> Grammar:
        """
        Creates a new grammar equivalent to this one, but having no terminals exactly 1 character long.
        """
        
        # TODO: Perhaps do in-place instead?
        
        new_grammar = Grammar()
        
        for rule in self.rules:
            if rule.lhs == self.new_start:
                continue  # Skip the new start rule
            
            new_rhs = []
            
            for symbol in rule.rhs:
                if not symbol.isTerminal():
                    new_rhs.append(symbol)
                    continue
                
                # Note that other custom types of terminals are ignored here
                if not isinstance(symbol, StrTerminal):
                    continue
                
                if len(symbol.value) == 0:
                    continue
                
                new_rhs.extend(StrTerminal(char) for char in symbol.value)
            
            new_grammar.add_rule(Rule(rule.lhs, new_rhs))
        
        new_grammar._prune_empty_terminals()
        
        return new_grammar
    
    def __repr__(self):
        return f"Grammar({', '.join(map(repr, self._rules))})"


__all__ = [
    "BaseSymbol",
    "Nonterminal",
    "Terminal",
    "StrTerminal",
    "Rule",
    "Grammar",
]
