from __future__ import annotations
import typing
import unittest

import set_path
from parser_test_base import ParserTestBase
from parsers_lib.all import *


class LRParserTest(ParserTestBase[LRParserAPI[StrTerminal]]):
    ParserAPIType: typing.ClassVar[typing.Type[LRParserAPI[StrTerminal]]] = LRParserAPI


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
