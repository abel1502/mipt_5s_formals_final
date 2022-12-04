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
    
    pass  # TODO


if __name__ == "__main__":
    exit(main())