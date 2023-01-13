from __future__ import annotations
import typing
import io


from .abstract_tokenizer import *


class CharTokenizer(Tokenizer):
    """
    A tokenizer that ensure single-char inputs from a source
    """
    
    _source: typing.Iterable[str]
    
    def __init__(self, source: typing.Iterable[str]):
        self._source = source

    def tokenize(self) -> typing.Generator[str, None, None]:
        for s in self._source:
            yield from s


__all__ = [
    "CharTokenizer",
]
