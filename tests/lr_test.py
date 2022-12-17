from __future__ import annotations
import typing
import unittest

import set_path
from parser_test_base import *
from parsers_lib.all import *


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
    ]
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 1)


class LR3ParserTest(LR1ParserTest):
    # Can't think of any unique test cases, but at least this does verify that LR(3) also works on LR(1) grammars...
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> LR1ParserTest.ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 3)
    


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
