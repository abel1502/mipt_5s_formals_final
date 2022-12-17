from __future__ import annotations
import typing
import itertools
import io
from collections import deque
from functools import wraps
import dataclasses
import enum


T = typing.TypeVar("T")


class PeekableStream(typing.Generic[T]):
    """
    A sequence object that adds support for peeking ahead a limited amount.
    """
    
    _source: typing.Final[typing.Iterator[T]]
    _limit: typing.Final[int]
    _peeked: typing.Final[typing.Deque[T]]
    _sentinel: typing.Final[T]
    _pos: int
    
    def __init__(self, source: typing.Iterable[T], limit: int, sentinel: T):
        self._source = source
        self._limit = limit
        self._peeked = deque()
        self._sentinel = sentinel
        self._pos = 0
        
        self._refill()
    
    @property
    def limit(self) -> int:
        return self._limit
    
    @property
    def sentinel(self) -> T:
        return self._sentinel
    
    def _refill(self) -> None:
        self._peeked.extend(itertools.islice(self._source, self._limit - len(self._peeked)))
        
        if len(self._peeked) < self._limit:
            self._source = itertools.repeat(self._sentinel)
            self._refill()
    
    def next(self) -> T:
        result: T = self._peeked.popleft()
        self._refill()
        self._pos += 1
        return result
    
    def skip(self, cnt: int) -> None:
        for i in range(cnt):
            self.next()
    
    def is_over(self) -> bool:
        return self.peek1() is self._sentinel
    
    def peek(self, cnt: int) -> typing.List[T]:
        if cnt > self._limit:
            raise ValueError("Cannot peek more than the limit")
        
        return list(itertools.islice(self._peeked, cnt))
    
    def peek1(self) -> T:
        return self.peek(1)[0]
    
    def __iter__(self) -> PeekableStreamIterator[T]:
        """
        Warning: read the docs for PeekableStreamIterator before using this!
        
        Iterating over this object might be counterintuitive in some ways.
        """
        
        return PeekableStreamIterator(self)
    
    def tell(self) -> int:
        """
        No seeking provided, but tell is here for a few weird cases
        """
        
        return self._pos


class PeekableStreamIterator(typing.Generic[T]):
    """
    A convenient iterator over a `PeekableStream` that actually only consumes an element after it has been iterated over.
    This way you can break from a loop at any point without having to worry about the stream being advanced.
    You will receive one sentinel value at the end of the stream, before iteration stops.
    
    Note that this is only really useful for 1-peeking, as you'll have no access to the consequent elements.
    
    Also note that iterating over a stream iterator advances the stream and every other iterator over it as well!
    """
    
    
    _master: typing.Final[PeekableStream[T]]
    _exhausted: bool
    _last_pos: int
    
    def __init__(self, master: PeekableStream[T]):
        self._master = master
        self._exhausted = False
        self._last_pos = -1  # Invalid value
    
    def __iter__(self) -> PeekableStreamIterator[T]:
        return self
    
    def __next__(self) -> T:
        if self._exhausted:
            raise StopIteration()
        
        # The extra check is necessary in case some other iterator has overaken us
        if self._last_pos == self._master.tell():
            self._master.next()
        
        self._last_pos = self._master.tell()
        
        if self._master.is_over():
            # Meant to take effect next time
            self._exhausted = True
        
        # print(f"peek >> {repr(self._master.peek1())}")
        
        return self._master.peek1()


# TODO: Inherit from TextIOBase?
class PeekableTextIO(PeekableStream[str]):
    @staticmethod
    def _iter_from_io(source: io.TextIOBase) -> typing.Generator[str, None, None]:
        while True:
            ch = source.read(1)
            
            if not ch:
                break
            
            yield ch
    
    def __init__(self, source: io.TextIOBase, limit: int, sentinel: str = ''):
        super().__init__(self._iter_from_io(source), limit, sentinel)

    def peek_str(self, cnt: int) -> str:
        return ''.join(self.peek(cnt))

    def peek_ch(self) -> str:
        return self.peek1()


__all__ = [
    "PeekableStream",
    "PeekableStreamIterator",
    "PeekableTextIO",
]
