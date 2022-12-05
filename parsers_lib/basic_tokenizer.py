from __future__ import annotations
import typing
import itertools
import abc
import enum
import dataclasses
import numbers
import io
import string
from functools import cached_property


from . import grammar
from .peekable_stream import PeekableTextIO
from .errors import ParseError


T = typing.TypeVar("T")
P = typing.TypeVar("P")
K = typing.TypeVar("K")


class Token(grammar.BaseSymbol):  # Automatically an ABC, but has no abstract methods
    def __init__(self):
        if type(self) is Token:
            raise TypeError("Token is an abstract class")
    
    def isTerminal() -> bool:
        return True


@dataclasses.dataclass(frozen=True)
class NameTok(Token):
    value: str


@dataclasses.dataclass(frozen=True)
class StringTok(Token):
    value: str
    quotes: str


@dataclasses.dataclass(frozen=True)
class NumberTok(Token):
    value: numbers.Number


@dataclasses.dataclass(frozen=True)
class PunctTok(Token, typing.Generic[P]):
    value: P


@dataclasses.dataclass(frozen=True)
class KwdTok(Token, typing.Generic[K]):
    value: K


@dataclasses.dataclass(frozen=True)
class EOFTok(Token):
    pass


@dataclasses.dataclass(frozen=True)
class BasicTokenizerConfig(typing.Generic[P, K]):
    parse_numbers: bool = True
    punct_lookup: typing.Mapping[str, P] = dataclasses.field(default_factory=dict)
    kwd_lookup: typing.Mapping[str, K] = dataclasses.field(default_factory=dict)
    # Note: if parse_numbers is True, then the first letter cannot be a digit
    #       (even if the identifier wouldn't form a valid number)
    name_chars: typing.Container[str] | typing.Callable[[str], bool] = \
        lambda ch: ch.isalnum() or ch == "_"
    space_chars: typing.Container[str] | typing.Callable[[str], bool] = \
        str.isspace
    line_comments: typing.Collection[str] = ()
    block_comments: typing.Mapping[str, str] = dataclasses.field(default_factory=dict)
    string_quotes: typing.Mapping[str, str] = dataclasses.field(default_factory=lambda: {
        "'": "'", '"': '"',
    })
    # chainable_strings: bool = False
    string_escapes: typing.Mapping[str, str] = dataclasses.field(default_factory=lambda: {
        "\\": "\\", "n": "\n", "t": "\t", "r": "\r", "0": "\0",
    })


_E = typing.TypeVar("_E", bound=enum.Enum)
def lookup_from_enum(enum: typing.Type[_E]) -> typing.Dict[str, _E]:
    return {member.value: member for member in enum}


class _Trie(typing.Generic[T]):
    @dataclasses.dataclass()
    class Node:
        verdict: T
        master: _Trie[T]
        children: typing.Dict[str, _Trie.Node] = dataclasses.field(default_factory=dict)
        
        def is_term(self) -> bool:
            return not self.children
        
        def get_child(self, ch: str) -> _Trie.Node:
            assert len(ch) == 1
            
            return self.children.get(ch, self.master._sentinel)
        
        def add_child(self, ch: str, verdict: T) -> _Trie.Node:
            return self.children.setdefault(ch, _Trie.Node(verdict, self.master))
    
    class WordChecker:
        _node: _Trie.Node
        _word: typing.List[str]
        
        def __init__(self, node: _Trie.Node):
            self._node = node
            self._word = []
        
        def is_term(self) -> bool:
            return self._node.is_term()
        
        def go(self, ch: str) -> None:
            assert len(ch) <= 1
            
            if not ch:
                return
            
            self._node = self._node.get_child(ch)
            self._word.append(ch)
        
        def restart(self) -> None:
            self._node = self._node.master._root
            self._word = []
        
        def get_verdict(self) -> T:
            return self._node.verdict
        
        def get_word(self) -> str:
            return "".join(self._word)
        
    
    _verdict_none: typing.Final[T]
    _root: typing.Final[Node]
    _sentinel: typing.Final[Node]
    
    def __init__(self, verdict_none: T):
        self._verdict_none = verdict_none
        self._root = self.Node(verdict_none, self)
        self._sentinel = self.Node(verdict_none, self)
    
    def add_word(self, word: str, verdict: T) -> None:
        verdict_none = self._verdict_none
        
        node = self._root
        for ch in word:
            node = node.add_child(ch, verdict_none)
        
        if node.verdict != verdict_none:
            raise ValueError(f"Word {word!r} already exists in the trie")
        
        node.verdict = verdict
    
    def add_wordlist(self, words: typing.Iterable[str], verdict: T) -> None:
        for word in words:
            self.add_word(word, verdict)
    
    def create_checker(self) -> _Trie.WordChecker:
        return self.WordChecker(self._root)


class BasicTokenizer(typing.Generic[P, K]):
    """
    A tokenizer for a common use case, where the tokens are keywords, punctuation and optionally numbers.
    """
    
    class _MiscTokVerdict(enum.IntEnum):
        NONE = enum.auto()
        PUNCT = enum.auto()
        LINE_COMMENT = enum.auto()
        BLOCK_COMMENT = enum.auto()
        STRING_QUOTE = enum.auto()
    
    class _StringVerdict(enum.IntEnum):
        NONE = enum.auto()
        ESCAPE = enum.auto()
        END_QUOTE = enum.auto()
    
    class _BlockCommentVerdict(enum.IntEnum):
        NONE = enum.auto()
        START = enum.auto()
        END = enum.auto()
    
    _config: BasicTokenizerConfig[P, K]
    _input: PeekableTextIO
    
    def __init__(self,
                 input: PeekableTextIO | io.TextIOBase | str,
                 config: BasicTokenizerConfig[P, K] = BasicTokenizerConfig()):
        if isinstance(input, str):
            input = io.StringIO(input)
        if not isinstance(input, PeekableTextIO):
            input = PeekableTextIO(input, 1)
        assert isinstance(input, PeekableTextIO)
        assert input.limit >= 1
        assert input.sentinel == ""
        
        self._config = config
        self._input = input
    
    @staticmethod
    def _build_checker_func(chars: typing.Container[str] | typing.Callable[[str], bool]) -> typing.Callable[[str], bool]:
        if not callable(chars):
            chars = lambda ch: ch in chars
        return chars

    @cached_property
    def _is_name_char(self) -> typing.Callable[[str], bool]:
        return self._build_checker_func(self._config.name_chars)
    
    @cached_property
    def _is_space_char(self) -> typing.Callable[[str], bool]:
        return self._build_checker_func(self._config.space_chars)
    
    @cached_property
    def _misc_tokens_trie(self) -> _Trie[_MiscTokVerdict]:
        trie = _Trie(self._MiscTokVerdict.NONE)
        
        trie.add_wordlist(self._config.line_comments, self._MiscTokVerdict.LINE_COMMENT)
        trie.add_wordlist(self._config.block_comments.keys(), self._MiscTokVerdict.BLOCK_COMMENT)
        trie.add_wordlist(self._config.punct_lookup.keys(), self._MiscTokVerdict.PUNCT)
        trie.add_wordlist(self._config.string_quotes.keys(), self._MiscTokVerdict.STRING_QUOTE)
        
        return trie
    
    @cached_property
    def _string_trie(self) -> _Trie[_StringVerdict]:
        trie = _Trie(self._StringVerdict.NONE)
        
        trie.add_wordlist(("\\" + k for k in self._config.string_escapes.keys()), self._StringVerdict.ESCAPE)
        trie.add_wordlist(self._config.string_quotes.values(), self._StringVerdict.END_QUOTE)
        
        return trie
    
    @cached_property
    def _block_comment_trie(self) -> _Trie[_StringVerdict]:
        trie = _Trie(self._BlockCommentVerdict.NONE)
        
        trie.add_wordlist(self._config.block_comments.keys(), self._BlockCommentVerdict.START)
        trie.add_wordlist(self._config.block_comments.values(), self._BlockCommentVerdict.END)
        
        return trie
    
    def tokenize(self) -> typing.Generator[Token, None, None]:
        # Locals to speed up access
        is_name_char = self._is_name_char
        is_space_char = self._is_space_char
        parse_numbers = self._config.parse_numbers
        
        # This is the first and last time I'll comment on this, so please note:
        # PeekableStreamIterator is implemented in a specific way that allows for
        # this kind of usage. All iterators are synchronized with the stream,
        # and the stream is advanced with a lag of 1. That means we can write
        # the tokenization logic in a way that is very easy to understand,
        # without any need for explicit lookaheads or backtracking.
        for ch in self._input:
            if is_space_char(ch) or not ch:
                continue
            elif parse_numbers and ch.isdigit():
                yield self._parse_number()
            elif is_name_char(ch):
                yield self._parse_name_or_kwd()
            else:
                # Yield from because for a comment it would be empty
                yield from self._parse_other()
    
    def _parse_number(self) -> NumberTok:
        raise NotImplementedError("Number parsing not yet implemented")
    
    def _parse_name_or_kwd(self) -> NameTok | KwdTok:
        name: NameTok = self._parse_name()
        
        return self._config.kwd_lookup.get(name.value, name)
    
    def _parse_name(self) -> NameTok:
        is_name_char = self._is_name_char
        
        name: typing.List[str] = []
        
        for ch in self._input:
            if not is_name_char(ch):
                break
            
            name.append(ch)
        
        return NameTok("".join(name))

    def _parse_other(self) -> typing.Generator[PunctTok, None, None]:
        checker = self._misc_tokens_trie.create_checker()
        
        for ch in self._input:
            if checker.is_term() or not ch:
                break
            
            checker.go(ch)
        
        verdict: self._MiscTokVerdict = checker.get_verdict()
        word: str = checker.get_word()
        
        if verdict == self._MiscTokVerdict.NONE:
            raise ParseError(f"Invalid punctuation/comment: {word}")
        
        if verdict == self._MiscTokVerdict.PUNCT:
            yield PunctTok(self._config.punct_lookup[word])
            return
        
        if verdict == self._MiscTokVerdict.STRING_QUOTE:
            yield self._parse_string(word)
            return
        
        if verdict == self._MiscTokVerdict.LINE_COMMENT:
            self._parse_line_comment()
            return
        
        if verdict == self._MiscTokVerdict.BLOCK_COMMENT:
            self._parse_block_comment(word)
            return
        
        assert False, "Unreachable"
    
    def _parse_string(self, start_quote: str) -> StringTok:
        end_quote: typing.Final[str] = self._config.string_quotes[start_quote]
        
        result: typing.List[str] = []
        
        checker = self._string_trie.create_checker()
        
        for ch in self._input:
            if checker.is_term():
                verdict: self._StringVerdict = checker.get_verdict()
                word: str = checker.get_word()
                
                if verdict == self._StringVerdict.NONE:
                    result.append(word)
                elif verdict == self._StringVerdict.ESCAPE:
                    assert word.startswith("\\")
                    
                    result.append(self.string_escapes[word.removeprefix("\\")])
                elif word == end_quote:  # verdict == self._StringVerdict.END_QUOTE
                    break
                
                checker.restart()
            
            if not ch:
                raise ParseError("Unterminated string")
            
            checker.go(ch)
        
        return StringTok("".join(result), start_quote)

    def _parse_line_comment(self) -> None:
        for ch in self._input:
            if ch == "\n":
                break
    
    def _parse_block_comment(self, start: str) -> None:
        end = self._config.block_comments[start]
        
        checker = self._block_comment_trie.create_checker()
        balance: int = 1
        
        for ch in self._input:
            if checker.is_term():
                verdict: self._BlockCommentVerdict = checker.get_verdict()
                word: str = checker.get_word()
                
                if verdict == self._BlockCommentVerdict.NONE:
                    pass
                elif verdict == self._BlockCommentVerdict.START:
                    balance += word == start
                elif verdict == self._BlockCommentVerdict.END:
                    balance -= word == end
                
                if balance == 0:
                    break
                
                checker.restart()
            
            if not ch:
                raise ParseError("Unterminated block comment")
            
            checker.go(ch)


__all__ = [
    "Token",
    "NameTok",
    "StringTok",
    "NumberTok",
    "PunctTok",
    "KwdTok",
    "EOFTok",
    "BasicTokenizerConfig",
    "lookup_from_enum",
    "BasicTokenizer",
]
