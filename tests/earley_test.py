from __future__ import annotations
import typing
import unittest

import set_path
from parser_test_base import *
from parsers_lib.all import *


class EarleyParserTest(ParserTestBase[EarleyParserAPI[StrTerminal]]):
    ParserAPIType: typing.ClassVar[typing.Type[EarleyParserAPI[StrTerminal]]] = EarleyParserAPI


del ParserTestBase  # Otherwise it will be run as a test case


if __name__ == "__main__":
    unittest.main()
