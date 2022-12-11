from __future__ import annotations
import typing
import unittest

import set_path
from parsers_lib.all import *


class EarleyParserTest(unittest.TestCase):
    parser_brackets: typing.ClassVar[EarleyParserAPI[StrTerminal]]
    parser_equal_ab: typing.ClassVar[EarleyParserAPI[StrTerminal]]
    parser_recursive: typing.ClassVar[EarleyParserAPI[StrTerminal]]
    
    
    @staticmethod
    def build_parser(grammar: Grammar | str) -> EarleyParserAPI[StrTerminal]:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return EarleyParserAPI(grammar)
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.parser_brackets = cls.build_parser("""
            <start> ::= "(" <start> ")" | <start> <start> | "";
        """)
        
        cls.parser_equal_ab = cls.build_parser("""
            <start> ::= "a" <start> "b" <start> | "b" <start> "a" <start> | "";
        """)
        
        cls.parser_recursive = cls.build_parser("""
            <start> ::= <a> | "abc";
            <a> ::= <a>;
        """)
    
    def check(self, parser: EarleyParserAPI[StrTerminal], data: str, expected: bool) -> None:
        with self.subTest(data=data):
            actual = parser.parse(CharTokenizer(data))
            
            self.assertEqual(actual, expected)
    
    def test_brackets(self) -> None:
        self.check(self.parser_brackets, "", True)
        self.check(self.parser_brackets, "()", True)
        self.check(self.parser_brackets, "()()", True)
        self.check(self.parser_brackets, "((()))", True)
        self.check(self.parser_brackets, "(()", False)
        self.check(self.parser_brackets, "())", False)
        self.check(self.parser_brackets, "((())", False)
        self.check(self.parser_brackets, "())(", False)
        self.check(self.parser_brackets, ")(", False)
        self.check(self.parser_brackets, ")()(", False)
        self.check(self.parser_brackets, "))((", False)
    
    def test_equal_ab(self) -> None:
        self.check(self.parser_equal_ab, "abab", True)
        self.check(self.parser_equal_ab, "aabb", True)
        self.check(self.parser_equal_ab, "bbaa", True)
        self.check(self.parser_equal_ab, "ba", True)
        self.check(self.parser_equal_ab, "", True)
        self.check(self.parser_equal_ab, "a", False)
        self.check(self.parser_equal_ab, "ababa", False)
        self.check(self.parser_equal_ab, "abbba", False)
        self.check(self.parser_equal_ab, "aabbb", False)
    
    def test_recursive(self) -> None:
        # This mostly just validates that the parser doesn't somehow loop infinitely.
        self.check(self.parser_recursive, "abc", True)
        self.check(self.parser_recursive, "", False)


if __name__ == "__main__":
    unittest.main()
