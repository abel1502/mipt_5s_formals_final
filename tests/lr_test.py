from __future__ import annotations
import typing
import unittest

import set_path
from parser_test_base import *
from parsers_lib.all import *
import parsers_lib._lr_parser_helpers as lr_parser_helpers


# All the common grammars are LR(1). For LR(k), separate tests are needed...
class LR1ParserTest(ParserTestBase[LRParserAPI[StrTerminal]]):
    ParserAPIType: typing.ClassVar[typing.Type[LRParserAPI[StrTerminal]]] = LRParserAPI
    
    parsers: typing.ClassVar[typing.List[ParserTestInfo]] = [
        # The example from the seminar
        ParserTestInfo(
            "seminar",
            """ <start> ::= <start> "a" <start> "b"; <start> ::= ''; """,
            {
                "aabb": True,
                "ab":   True,
                "ba":   False,
                "":     True,
            }
        ),
        
        # Won't work because we're using First_k instead of EFF, and this grammar has a non-generating rule
        # ParserTestBase.get_parser_info("recursive")
        
        # Has a shift-reduce conflict
        # ParserTestBase.get_parser_info("equal_ab"),
        
        # Also has a shift-reduce conflict
        # ParserTestBase.get_parser_info("brackets"),
        
        # Indirect recursion trap, but also R-R conflict
        # ParserTestInfo(
        #     "indirect_recursion",
        #     """ <start> ::= <A>; <A> ::= <B>; <B> ::= <A> | "a"; """,
        #     {
        #         "a":  True,
        #         "b":  False,
        #         "aa": False,
        #         "":   False,
        #     }
        # ),
        
        # Proper indirect recursion test (should work with both LR(1) and LR(2))
        ParserTestInfo(
            "indirect_recursion",
            """
            <start> ::= <A> "!";
            <A> ::= "a" <B> | "";
            <B> ::= "b" <A> | "";
            """,
            {
                "!":       True,
                "a!":      True,
                "ab!":      True,
                "ababa!":  True,
                "ababab!": True,
                "":        False,
                "ab":      False,
                "aba":     False,
                "bab!":    False,
                "baba!":   False,
                "abba!":   False,
                "ababaa!": False,
            }
        ),
    ]
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 1)


class LR2ParserTest(LR1ParserTest):
    # Can't think of any unique test cases, but at least this does verify that LR(3) also works on LR(1) grammars...
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> LR1ParserTest.ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 2)
    
    parsers: typing.ClassVar[typing.List[ParserTestInfo]] = LR1ParserTest.parsers + [
        # LR(2), but not LR(1)
        ParserTestInfo(
            "seminar",
            """
                <start> ::= <A> <B>;
                <A> ::= "a";
                <B> ::= <C> <D> | "a" <E>;
                <C> ::= "ab";
                <D> ::= "bb";
                <E> ::= "bba";
            """,
            {
                "aabbb": True,
                "aabba": True,
                "babba": False,
                "a":     False,
            }
        ),
    ]


class FirstKTest(unittest.TestCase):
    K: typing.ClassVar[int] = 2
    GRAMMAR_DEF: typing.ClassVar[str] = """ <start> ::= <start> "a" <start> "b"; <start> ::= ''; """
    
    grammar: typing.ClassVar[Grammar]
    vgk_builder = lr_parser_helpers.VGkBuilder
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.grammar = metaparse_bnf_grammar(data=cls.GRAMMAR_DEF)
    
    @classmethod
    def tearDownClass(cls) -> None:
        del cls.grammar
    
    def setUp(self) -> None:
        self.vgk_builder = lr_parser_helpers.VGkBuilder(self.grammar, self.K)
    
    def tearDown(self) -> None:
        del self.vgk_builder
    
    def check_first_k(self,
                      rule_symbols: typing.Sequence[BaseSymbol],
                      continuation: str,
                      expected: typing.Set[str],
                      debug: bool = False):
        with self.subTest(rule_symbols=rule_symbols, continuation=continuation):
            continuation: typing.Tuple[str, ...] = tuple(continuation)
            expected: typing.Set[typing.Tuple[str, ...]] = {tuple(x) for x in expected}
            
            assert len(continuation) <= self.K, f"The test is conducted for k = {self.K}"
            
            actual: typing.Set[typing.Tuple[str, ...]] = set(self.vgk_builder.first_k(rule_symbols, continuation))
            
            if debug:
                print(">>>", actual, flush=True)
                return
            
            self.assertEqual(actual, expected)
    
    def test_first_k(self) -> None:
        self.check_first_k([], "", {""})
        self.check_first_k([Nonterminal("start")], "", {"", "aa", "ab"})
        self.check_first_k([Nonterminal("start")], "a", {"a", "aa", "ab"})
        self.check_first_k([Nonterminal("start"), StrTerminal("b"), Nonterminal("start")], "", {"b", "aa", "ab", "ba"})


# Could properly separate FirstKTest from the abstract base, but won't bother
class ExtraFirstKTest1(FirstKTest):
    K: typing.Final[int] = 2
    GRAMMAR_DEF: typing.ClassVar[str] = """
        <start> ::= <A> "!";
        <A> ::= "a" <B> | "";
        <B> ::= "b" <A> | "";
    """
    
    def test_first_k(self) -> None:
        self.check_first_k([], "", {""})
        self.check_first_k([Nonterminal("A")], "", {"", "a", "ab"})


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
