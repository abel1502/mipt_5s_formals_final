from __future__ import annotations
import typing
import unittest
import dataclasses

import set_path
from parsers_lib.all import *


P = typing.TypeVar("P", bound=ParserAPI[bool, StrTerminal])


@dataclasses.dataclass
class ParserTestInfo(typing.Generic[P]):
    name: str
    grammar: str
    tests: typing.Dict[str, bool]
    parser: P | None = None


class ParserTestBase(unittest.TestCase, typing.Generic[P]):
    ParserAPIType: typing.ClassVar[typing.Type[P]] = ParserAPI
    
    parsers: typing.ClassVar[typing.List[ParserTestInfo[P]]] = [
        ParserTestInfo(
            "brackets",
            """ <start> ::= "(" <start> ")" | <start> <start> | ""; """,
            {
                "":       True,
                "()":     True,
                "()()":   True,
                "((()))": True,
                "(()":    False,
                "())":    False,
                "((())":  False,
                "())(":   False,
                ")(":     False,
                ")()(":   False,
                "))((":   False,
            }
        ),
        ParserTestInfo(
            "equal_ab",
            """ <start> ::= "a" <start> "b" <start> | "b" <start> "a" <start> | ""; """,
            {
                "abab":  True,
                "aabb":  True,
                "bbaa":  True,
                "ba":    True,
                "":      True,
                "a":     False,
                "ababa": False,
                "abbba": False,
                "aabbb": False,
            }
        ),
        ParserTestInfo(
            "recursive",
            """ <start> ::= <a> | "abc"; <a> ::= <a>; """,
            {
                "abc": True,
                "a":   False,
                "":    False,
            }
        ),
    ]
    
    @classmethod
    def get_parser_info(cls, name: str) -> ParserTestInfo:
        for info in cls.parsers:
            if info.name == name:
                return info
        
        raise KeyError(f"Parser {name!r} not found")
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar)
    
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        
        for info in cls.parsers:
            setattr(cls, f"test_{info.name}", lambda self, info=info: self.check_all(info))
    
    @classmethod
    def setUpClass(cls) -> None:
        assert cls is not ParserTestBase, "ParserTestBase is an abstract base class, not a test case"
        
        for info in cls.parsers:
            info.parser = cls.build_parser(info.grammar)
    
    @classmethod
    def tearDownClass(cls) -> None:
        for info in cls.parsers:
            info.parser = None
    
    def check(self, parser: ParserAPIType, data: str, expected: bool) -> None:
        with self.subTest(data=data):
            actual = parser.parse(CharTokenizer(data))
            
            self.assertEqual(actual, expected)
    
    def check_all(self, info: ParserTestInfo) -> None:
        for data, expected in info.tests.items():
            self.check(info.parser, data, expected)


__all__ = [
    "ParserTestInfo",
    "ParserTestBase",
]


if __name__ == "__main__":
    assert False, "This file is not a unit test!"
