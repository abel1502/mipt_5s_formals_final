from __future__ import annotations
import typing
import io
import enum


from .basic_tokenizer import *
from .peekable_stream import PeekableStream
from .grammar import *
from .errors import ParseError


class BNFMetaParser:
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
        line_comments=("//",),
        block_comments={"/*": "*/"},
    )
    
    _source: PeekableStream[Token]
    _grammar: Grammar
    
    def __init__(self, source: str | io.TextIOBase):
        self._source = PeekableStream(BasicTokenizer(source, self._TOKENIZER_CONFIG).tokenize(), limit=1, sentinel=EOFTok())
        self._grammar = Grammar(start="start")
    
    def parse(self) -> Grammar:
        self._parse_grammar()
        
        return self._grammar
    
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
    
    def _parse_rule(self) -> None:
        lhs: Nonterminal = self._parse_nonterminal()
        
        for rhs in self._parse_rhs_variants():
            self._grammar.add_rule(Rule(lhs, rhs))
        
        self._expect(PunctTok(self._Punct.SEMICOLON))
    
    def _parse_rhs_variants(self) -> typing.Generator[typing.List[BaseSymbol], None, None]:
        while True:
            yield self._parse_rhs()
            
            if self._source.peek1() != PunctTok(self._Punct.OR):
                break
            
            self._source.next()
    
    def _parse_rhs(self) -> typing.List[BaseSymbol]:
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
    
    def _parse_terminal(self) -> Terminal:
        return Terminal(self._expect(StringTok).value)

