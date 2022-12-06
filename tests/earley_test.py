from __future__ import annotations
import typing
import unittest

import set_path
from parsers_lib.all import *


class EarleyParserTest(unittest.TestCase):
    cfg_brackets: typing.ClassVar[EarleyParserConfig[StrTerminal]]
    cfg_equal_ab: typing.ClassVar[EarleyParserConfig[StrTerminal]]
    cfg_recursive: typing.ClassVar[EarleyParserConfig[StrTerminal]]
    
    parser_brackets: EarleyParser[StrTerminal]
    parser_equal_ab: EarleyParser[StrTerminal]
    parser_recursive: EarleyParser[StrTerminal]
    
    
    @staticmethod
    def build_parser_config(grammar: Grammar | str):
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return EarleyParserConfig(grammar=grammar)
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg_brackets = cls.build_parser_config("""
            <start> ::= "(" <start> ")" | <start> <start> | "";
        """)
        
        cls.cfg_equal_ab = cls.build_parser_config("""
            <start> ::= "a" <start> "b" <start> | "b" <start> "a" <start> | "";
        """)
        
        cls.cfg_recursive = cls.build_parser_config("""
            <start> ::= <a> | "abc";
            <a> ::= <a>;
        """)
    
    def setUp(self) -> None:
        self.parser_brackets = EarleyParser(self.cfg_brackets)
        self.parser_equal_ab = EarleyParser(self.cfg_equal_ab)
        self.parser_recursive = EarleyParser(self.cfg_recursive)
    
    def tearDown(self) -> None:
        del self.parser_brackets
        del self.parser_equal_ab
        del self.parser_recursive
    
    def check(self, parser: EarleyParser[StrTerminal], data: str, expected: bool) -> None:
        with self.subTest(data=data):
            parser.feed(CharTokenizer(data))
            actual = parser.parse()
            
            self.assertEqual(actual, expected)
    
    def test_brackets(self) -> None:
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
    
    


if __name__ == "__main__":
    unittest.main()
