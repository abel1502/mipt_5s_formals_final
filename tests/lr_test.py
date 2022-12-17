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
        ParserTestInfo(
            "seminar",  # The example from the seminar
            """ <start> ::= <start> "a" <start> "b"; <start> ::= ''; """,
            {
                "aabb": True,
                "ab":   True,
                "ba":   False,
                "":     True,
            }
        ),
        # ParserTestBase.get_parser_info("recursive"),
    ]
    
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 1)


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
