from __future__ import annotations
import typing
import io
import enum
import os


from .basic_tokenizer import *
from .peekable_stream import PeekableStream
from .grammar import *
from .errors import *
from .abstract_parser import Parser


# TODO: Add ParserAPI?
class BNFMetaParser(Parser[Grammar, Token]):
    class _Punct(enum.Enum):
        RULE_DEF = "::="
        OR = "|"
        LEFT_BRACE = "<"
        RIGHT_BRACE = ">"
        SEMICOLON = ";"

    _TOKENIZER_CONFIG: typing.Final[BasicTokenizerConfig[_Punct, None]] = BasicTokenizerConfig(
        parse_numbers=False,
        punct_lookup=lookup_from_enum(_Punct),
        name_chars=lambda ch: ch.isalnum() or ch in "-_",
        line_comments=("//", "#"),
        block_comments={"/*": "*/"},
    )
    
    _source: PeekableStream[Token]
    _grammar: Grammar
    
    def __init__(self):
        pass
    
    @staticmethod
    def make_tokenizer(source: typing.Iterable[str]) -> BasicTokenizer[_Punct, None]:
        return BasicTokenizer(source, BNFMetaParser._TOKENIZER_CONFIG)
    
    def feed(self, source: typing.Iterable[Token], start_nonterm: str = "start") -> None:
        """
        Supply a source of text to parse. Note that it doesn't add to the existing source, it replaces it.
        """
        
        self._source = PeekableStream(source, limit=1, sentinel=EOFTok())
        self._grammar = Grammar(start=start_nonterm)
    
    def parse(self) -> Grammar:
        if not self._is_initialized():
            raise RuntimeError("Parser is not initialized")
        
        self._parse_grammar()
        
        self._uninitialize()
        
        self._grammar = self._grammar.split_long_terminals()
        
        return self._grammar
    
    def _is_initialized(self) -> bool:
        return hasattr(self, "_source")
    
    def _uninitialize(self) -> None:
        del self._source
    
    def _expect(self, expected: Token | typing.Type[Token]) -> Token:
        tok = self._source.peek1()
        
        if isinstance(expected, type):
            if not isinstance(tok, expected):
                raise ParseError(f"Expected {expected.__qualname__}, got {tok.__class__.__qualname__} ({tok})")
        else:
            if tok != expected:
                raise ParseError(f"Expected {expected}, got {tok}")
        
        return self._source.next()
    
    def _parse_grammar(self) -> None:
        while not self._source.is_over():
            self._parse_rule()
        
        self._expect(EOFTok)
    
    def _parse_rule(self) -> None:
        lhs: Nonterminal = self._parse_nonterminal()
        
        self._expect(PunctTok(self._Punct.RULE_DEF))
        
        for rhs in self._parse_rhs_variants():
            self._grammar.add_rule(Rule(lhs, rhs))
        
        self._expect(PunctTok(self._Punct.SEMICOLON))
    
    def _parse_rhs_variants(self) -> typing.Generator[typing.Collection[BaseSymbol], None, None]:
        while True:
            yield self._parse_rhs()
            
            if self._source.peek1() != PunctTok(self._Punct.OR):
                break
            
            self._source.next()
    
    def _parse_rhs(self) -> typing.Collection[BaseSymbol]:
        result: typing.List[BaseSymbol] = []
        
        while True:
            tok = self._source.peek1()
            
            if isinstance(tok, PunctTok) and tok.value in (self._Punct.OR, self._Punct.SEMICOLON):
                break
            
            result.append(self._parse_any_symbol())
        
        return result
    
    def _parse_any_symbol(self) -> BaseSymbol:
        tok = self._source.peek1()
        
        if tok == PunctTok(self._Punct.LEFT_BRACE):
            return self._parse_nonterminal()
        
        if isinstance(tok, StringTok):
            return self._parse_terminal()
        
        raise ParseError("Expected terminal or nonterminal, got {tok}")
    
    def _parse_nonterminal(self) -> Nonterminal:
        self._expect(PunctTok(self._Punct.LEFT_BRACE))
        
        name = self._expect(NameTok).value
        
        self._expect(PunctTok(self._Punct.RIGHT_BRACE))
        
        return Nonterminal(name)
    
    def _parse_terminal(self) -> StrTerminal:
        # TODO: Split into many single-character terminals?
        # I'll let the user do that manually for now, but it might be a good idea to do it automatically.
        return StrTerminal(self._expect(StringTok).value)


@typing.overload
def metaparse_bnf_grammar(*, data: str | io.TextIOBase) -> Grammar:
    ...

@typing.overload
def metaparse_bnf_grammar(*, path: os.PathLike) -> Grammar:
    ...

def metaparse_bnf_grammar(*, data=None, path=None) -> Grammar:
    assert data is None or path is None, "Both data and path specified"
    
    parser = BNFMetaParser()
    
    if path is not None:
        with open(path, "r") as f:
            parser.feed(BNFMetaParser.make_tokenizer(f))
            return parser.parse()
    
    if data is not None:
        parser.feed(BNFMetaParser.make_tokenizer(data))
        return parser.parse()
    
    assert False, "Neither data nor path specified"


__all__ = [
    "BNFMetaParser",
    "metaparse_bnf_grammar",
]
