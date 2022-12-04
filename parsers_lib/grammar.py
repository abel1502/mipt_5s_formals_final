from __future__ import annotations
import typing
import dataclasses


@dataclasses.dataclass(frozen=True)
class BaseSymbol:
    pass


@dataclasses.dataclass(frozen=True, repr=False)
class Nonterminal(BaseSymbol):
    name: str
    
    def __repr__(self):
        return self.name


@dataclasses.dataclass(frozen=True, repr=False)
class Terminal(BaseSymbol):
    value: str
    
    def __repr__(self):
        return repr(self.value)


@dataclasses.dataclass(frozen=True, repr=False)
class Rule:
    lhs: Nonterminal
    rhs: typing.List[BaseSymbol] = dataclasses.field(default_factory=list)
    
    def __len__(self):
        return len(self._rules)
    
    def __repr__(self):
        return f"<{self.lhs} -> {' '.join(map(str, self.rhs))}>"


class Grammar:
    _rules: typing.List[Rule]
    
    def __init__(self, rules: typing.Iterable[Rule] | None):
        if rules is None:
            rules = []
        
        self._rules = list(rules)
    
    @property
    def rules(self) -> typing.Iterable[Rule]:
        return self._rules

    def add_rule(self, rule: Rule):
        self._rules.append(rule)
    
    def get_rules_by_lhs(self, lhs: Nonterminal) -> typing.Iterable[Rule]:
        return filter(lambda rule: rule.lhs == lhs, self._rules)
    
    def __repr__(self):
        return f"Grammar({', '.join(map(repr, self._rules))})"


__all__ = [
    "BaseSymbol",
    "Nonterminal",
    "Terminal",
    "Rule",
    "Grammar",
]
