# -*- coding: utf-8 -*-
"""
    Pygments basic API tests
    ~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2006-2019 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import print_function

import random
import unittest

from pygments import lexers, formatters, lex, format
from pygments.token import _TokenType, Text
from pygments.lexer import RegexLexer
from pygments.formatters.img import FontNotFound
from pygments.util import text_type, StringIO, BytesIO, xrange, ClassNotFound

import support

TESTFILE, TESTDIR = support.location(__file__)

test_content = [chr(i) for i in xrange(33, 128)] * 5
random.shuffle(test_content)
test_content = ''.join(test_content) + '\n'


def test_lexer_instantiate_all():
    # instantiate every lexer, to see if the token type defs are correct
    def verify(name):
        getattr(lexers, name)
    for x in lexers.LEXERS:
        yield verify, x


def test_lexer_classes():
    # test that every lexer class has the correct public API
    def verify(cls):
        assert type(cls.name) is str
        for attr in 'aliases', 'filenames', 'alias_filenames', 'mimetypes':
            assert hasattr(cls, attr)
            assert type(getattr(cls, attr)) is list, \
                "%s: %s attribute wrong" % (cls, attr)
        result = cls.analyse_text("abc")
        assert isinstance(result, float) and 0.0 <= result <= 1.0
        result = cls.analyse_text(".abc")
        assert isinstance(result, float) and 0.0 <= result <= 1.0

        assert all(al.lower() == al for al in cls.aliases)

        inst = cls(opt1="val1", opt2="val2")
        if issubclass(cls, RegexLexer):
            if not hasattr(cls, '_tokens'):
                # if there's no "_tokens", the lexer has to be one with
                # multiple tokendef variants
                assert cls.token_variants
                for variant in cls.tokens:
                    assert 'root' in cls.tokens[variant]
            else:
                assert 'root' in cls._tokens, \
                       '%s has no root state' % cls

        if cls.name in ['XQuery', 'Opa']:   # XXX temporary
            return

        try:
            tokens = list(inst.get_tokens(test_content))
        except KeyboardInterrupt:
            raise KeyboardInterrupt(
                'interrupted %s.get_tokens(): test_content=%r' %
                (cls.__name__, test_content))
        txt = ""
        for token in tokens:
            assert isinstance(token, tuple)
            assert isinstance(token[0], _TokenType)
            assert isinstance(token[1], text_type)
            txt += token[1]
        assert txt == test_content, "%s lexer roundtrip failed: %r != %r" % \
            (cls.name, test_content, txt)

    for lexer in lexers._iter_lexerclasses(plugins=False):
        yield verify, lexer


def test_lexer_options():
    # test that the basic options work
    def ensure(tokens, output):
        concatenated = ''.join(token[1] for token in tokens)
        assert concatenated == output, \
            '%s: %r != %r' % (lexer, concatenated, output)

    def verify(cls):
        inst = cls(stripnl=False)
        ensure(inst.get_tokens('a\nb'), 'a\nb\n')
        ensure(inst.get_tokens('\n\n\n'), '\n\n\n')
        inst = cls(stripall=True)
        ensure(inst.get_tokens('   \n  b\n\n\n'), 'b\n')
        # some lexers require full lines in input
        if ('ConsoleLexer' not in cls.__name__ and
            'SessionLexer' not in cls.__name__ and
            not cls.__name__.startswith('Literate') and
            cls.__name__ not in ('ErlangShellLexer', 'RobotFrameworkLexer')):
            inst = cls(ensurenl=False)
            ensure(inst.get_tokens('a\nb'), 'a\nb')
            inst = cls(ensurenl=False, stripall=True)
            ensure(inst.get_tokens('a\nb\n\n'), 'a\nb')

    for lexer in lexers._iter_lexerclasses(plugins=False):
        if lexer.__name__ == 'RawTokenLexer':
            # this one is special
            continue
        yield verify, lexer


def test_get_lexers():
    # test that the lexers functions work
    def verify(func, args):
        x = func(opt='val', *args)
        assert isinstance(x, lexers.PythonLexer)
        assert x.options["opt"] == "val"

    for func, args in [(lexers.get_lexer_by_name, ("python",)),
                       (lexers.get_lexer_for_filename, ("test.py",)),
                       (lexers.get_lexer_for_mimetype, ("text/x-python",)),
                       (lexers.guess_lexer, ("#!/usr/bin/python -O\nprint",)),
                       (lexers.guess_lexer_for_filename, ("a.py", "<%= @foo %>"))
                       ]:
        yield verify, func, args

    for cls, (_, lname, aliases, _, mimetypes) in lexers.LEXERS.items():
        assert cls == lexers.find_lexer_class(lname).__name__

        for alias in aliases:
            assert cls == lexers.get_lexer_by_name(alias).__class__.__name__

        for mimetype in mimetypes:
            assert cls == lexers.get_lexer_for_mimetype(mimetype).__class__.__name__

    try:
        lexers.get_lexer_by_name(None)
    except ClassNotFound:
        pass
    else:
        raise Exception


def test_formatter_public_api():
    # test that every formatter class has the correct public API
    ts = list(lexers.PythonLexer().get_tokens("def f(): pass"))
    string_out = StringIO()
    bytes_out = BytesIO()

    def verify(formatter):
        info = formatters.FORMATTERS[formatter.__name__]
        assert len(info) == 5
        assert info[1], "missing formatter name"
        assert info[2], "missing formatter aliases"
        assert info[4], "missing formatter docstring"

        try:
            inst = formatter(opt1="val1")
        except (ImportError, FontNotFound) as e:
            raise support.SkipTest(e)

        try:
            inst.get_style_defs()
        except NotImplementedError:
            # may be raised by formatters for which it doesn't make sense
            pass

        if formatter.unicodeoutput:
            inst.format(ts, string_out)
        else:
            inst.format(ts, bytes_out)

    for name in formatters.FORMATTERS:
        formatter = getattr(formatters, name)
        yield verify, formatter


def test_formatter_encodings():
    from pygments.formatters import HtmlFormatter

    # unicode output
    fmt = HtmlFormatter()
    tokens = [(Text, u"ä")]
    out = format(tokens, fmt)
    assert type(out) is text_type
    assert u"ä" in out

    # encoding option
    fmt = HtmlFormatter(encoding="latin1")
    tokens = [(Text, u"ä")]
    assert u"ä".encode("latin1") in format(tokens, fmt)

    # encoding and outencoding option
    fmt = HtmlFormatter(encoding="latin1", outencoding="utf8")
    tokens = [(Text, u"ä")]
    assert u"ä".encode("utf8") in format(tokens, fmt)


def test_formatter_unicode_handling():
    # test that the formatter supports encoding and Unicode
    tokens = list(lexers.PythonLexer(encoding='utf-8').
                  get_tokens("def f(): 'ä'"))

    def verify(formatter):
        try:
            inst = formatter(encoding=None)
        except (ImportError, FontNotFound) as e:
            # some dependency or font not installed
            raise support.SkipTest(e)

        if formatter.name != 'Raw tokens':
            out = format(tokens, inst)
            if formatter.unicodeoutput:
                assert type(out) is text_type, '%s: %r' % (formatter, out)

            inst = formatter(encoding='utf-8')
            out = format(tokens, inst)
            assert type(out) is bytes, '%s: %r' % (formatter, out)
            # Cannot test for encoding, since formatters may have to escape
            # non-ASCII characters.
        else:
            inst = formatter()
            out = format(tokens, inst)
            assert type(out) is bytes, '%s: %r' % (formatter, out)

    for formatter, info in formatters.FORMATTERS.items():
        # this tests the automatic importing as well
        fmter = getattr(formatters, formatter)
        yield verify, fmter


def test_get_formatters():
    # test that the formatters functions work
    x = formatters.get_formatter_by_name("html", opt="val")
    assert isinstance(x, formatters.HtmlFormatter)
    assert x.options["opt"] == "val"

    x = formatters.get_formatter_for_filename("a.html", opt="val")
    assert isinstance(x, formatters.HtmlFormatter)
    assert x.options["opt"] == "val"


def test_styles():
    # minimal style test
    from pygments.formatters import HtmlFormatter
    HtmlFormatter(style="pastie")


def test_bare_class_handler():
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer
    try:
        lex('test\n', PythonLexer)
    except TypeError as e:
        assert 'lex() argument must be a lexer instance' in str(e)
    else:
        assert False, 'nothing raised'
    try:
        format([], HtmlFormatter)
    except TypeError as e:
        assert 'format() argument must be a formatter instance' in str(e)
    else:
        assert False, 'nothing raised'


class FiltersTest(unittest.TestCase):

    def test_basic(self):
        filters_args = [
            ('whitespace', {'spaces': True, 'tabs': True, 'newlines': True}),
            ('whitespace', {'wstokentype': False, 'spaces': True}),
            ('highlight', {'names': ['isinstance', 'lexers', 'x']}),
            ('codetagify', {'codetags': 'API'}),
            ('keywordcase', {'case': 'capitalize'}),
            ('raiseonerror', {}),
            ('gobble', {'n': 4}),
            ('tokenmerge', {}),
        ]
        for x, args in filters_args:
            lx = lexers.PythonLexer()
            lx.add_filter(x, **args)
            with open(TESTFILE, 'rb') as fp:
                text = fp.read().decode('utf-8')
            tokens = list(lx.get_tokens(text))
            self.assertTrue(all(isinstance(t[1], text_type)
                                for t in tokens),
                            '%s filter did not return Unicode' % x)
            roundtext = ''.join([t[1] for t in tokens])
            if x not in ('whitespace', 'keywordcase', 'gobble'):
                # these filters change the text
                self.assertEqual(roundtext, text,
                                 "lexer roundtrip with %s filter failed" % x)

    def test_raiseonerror(self):
        lx = lexers.PythonLexer()
        lx.add_filter('raiseonerror', excclass=RuntimeError)
        self.assertRaises(RuntimeError, list, lx.get_tokens('$'))

    def test_whitespace(self):
        lx = lexers.PythonLexer()
        lx.add_filter('whitespace', spaces='%')
        with open(TESTFILE, 'rb') as fp:
            text = fp.read().decode('utf-8')
        lxtext = ''.join([t[1] for t in list(lx.get_tokens(text))])
        self.assertFalse(' ' in lxtext)

    def test_keywordcase(self):
        lx = lexers.PythonLexer()
        lx.add_filter('keywordcase', case='capitalize')
        with open(TESTFILE, 'rb') as fp:
            text = fp.read().decode('utf-8')
        lxtext = ''.join([t[1] for t in list(lx.get_tokens(text))])
        self.assertTrue('Def' in lxtext and 'Class' in lxtext)

    def test_codetag(self):
        lx = lexers.PythonLexer()
        lx.add_filter('codetagify')
        text = u'# BUG: text'
        tokens = list(lx.get_tokens(text))
        self.assertEqual('# ', tokens[0][1])
        self.assertEqual('BUG', tokens[1][1])

    def test_codetag_boundary(self):
        # ticket #368
        lx = lexers.PythonLexer()
        lx.add_filter('codetagify')
        text = u'# DEBUG: text'
        tokens = list(lx.get_tokens(text))
        self.assertEqual('# DEBUG: text', tokens[0][1])
