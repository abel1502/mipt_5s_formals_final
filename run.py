from __future__ import annotations
import typing
import argparse

from parsers_lib import all as parsers


parser = argparse.ArgumentParser(
    description="""
    An interactive tool for some manual testing of the library.
    """
)


def main():
    args = parser.parse_args()
    
    # print(list(parsers.BasicTokenizer(sample_grammar, parsers.BNFMetaParser._TOKENIZER_CONFIG).tokenize()))
    print(parsers.metaparse_bnf_grammar(path="grammars/sample.bnf"))


if __name__ == "__main__":
    exit(main())