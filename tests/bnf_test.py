from __future__ import annotations
import typing
import unittest

import set_path
from parsers_lib.all import *


class BNFMetaParserTest(unittest.TestCase):
    def check(self, source: str, expected: Grammar) -> None:
        actual = metaparse_bnf_grammar(data=source)
        
        self.assertEqual(actual.nonterminals, expected.nonterminals)
        self.assertEqual(actual.start, expected.start)
        self.assertEqual(actual.rules, expected.rules)
    
    def test_simple(self) -> None:
        self.check("""
            <start> ::= <a> <several-bs> | <3-c>;
            <a> ::= "a";  # comment
            // Another comment
            <several-bs> ::= "b" /* comment inside block */ <several-bs> | "b";
            <3-c> ::= "c c b";
        """, Grammar(
            rules={
                Rule(Nonterminal("start"), [Nonterminal("a"), Nonterminal("several-bs")]),
                Rule(Nonterminal("start"), [Nonterminal("3-c")]),
                Rule(Nonterminal("a"), [StrTerminal("a")]),
                Rule(Nonterminal("several-bs"), [StrTerminal("b"), Nonterminal("several-bs")]),
                Rule(Nonterminal("several-bs"), [StrTerminal("b")]),
                Rule(Nonterminal("3-c"), [StrTerminal("c c b")]),
            }, start=Nonterminal("start")
        ))
    
    def test_comments(self) -> None:
        self.check("""
            #!/bin/shabash whatever
            
            // comment
            <start> ::= "aboba" /* "ababa" /* nested comments, woah! */*/ "abiba"
                # another comment
                ; //Yup
        # No newline""", Grammar(
            rules={
                Rule(Nonterminal("start"), [StrTerminal("aboba"), StrTerminal("abiba")]),
            }, start=Nonterminal("start")
        ))
    
    def test_terminals(self) -> None:
        self.check(r"""
            <start> ::= "a" | 'b' | "\\\"'\'c\n\r" | '\\\"d"\'\r\n';
        """, Grammar(
            rules={
                Rule(Nonterminal("start"), [StrTerminal("a")]),
                Rule(Nonterminal("start"), [StrTerminal("b")]),
                Rule(Nonterminal("start"), [StrTerminal("\\\"\'\'c\n\r")]),
                Rule(Nonterminal("start"), [StrTerminal("\\\"d\"\'\r\n")]),
            }, start=Nonterminal("start")
        ))


if __name__ == "__main__":
    unittest.main()
