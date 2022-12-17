from __future__ import annotations
import typing
import unittest

import set_path
from parser_test_base import ParserTestBase
from parsers_lib.all import *


# All the common grammars are LR(1). For LR(k), separate tests are needed...
class LR1ParserTest(ParserTestBase[LRParserAPI[StrTerminal]]):
    @classmethod
    def build_parser(cls, grammar: Grammar | str) -> ParserAPIType:
        if isinstance(grammar, str):
            grammar = metaparse_bnf_grammar(data=grammar)
        
        return cls.ParserAPIType(grammar, "", 1)
    
    ParserAPIType: typing.ClassVar[typing.Type[LRParserAPI[StrTerminal]]] = LRParserAPI


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
