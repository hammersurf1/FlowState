import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest
from clipboard_html import html_to_markdown, _cf_html_fragment
from rich_text_formatter import RichTextFormatter, KeyAction, TypeAction

# Shaped like what Google Docs puts on the clipboard (note the font-weight:normal <b> wrapper)
DOCS = ('<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-1">'
        '<h1 dir="ltr"><span style="font-weight:700">Hello Professor</span></h1>'
        '<p dir="ltr"><span style="font-weight:400">I am writing about </span>'
        '<span style="font-weight:700">the deadline </span><span style="font-style:italic">please</span>'
        '<span> </span><span style="text-decoration:underline">now</span></p>'
        '<ul><li dir="ltr" aria-level="1"><p dir="ltr"><span>First</span></p></li>'
        '<ul><li aria-level="2"><p><span>Nested</span></p></li></ul>'
        '<li aria-level="1"><p><span>Second</span></p></li></ul>'
        '<p dir="ltr"><span style="text-decoration:line-through">old</span> new</p></b>')


def test_docs_html_becomes_markdown():
    assert html_to_markdown(DOCS).split("\n") == [
        "# Hello Professor",
        "I am writing about **the deadline** _please_ ___now___",
        "- First", "  - Nested", "- Second",
        "~~old~~ new",
    ]


def test_markers_hug_text_not_spaces():
    md = html_to_markdown("<p>a <b> bold </b> b</p>")
    assert md == "a **bold** b"


def test_nested_same_style_does_not_cancel_out():
    assert html_to_markdown("<p><b><span style='font-weight:700'>x</span></b> y</p>") == "**x** y"


def test_plain_paragraphs_return_none_so_plain_text_is_used():
    assert html_to_markdown("<div><span style='color:red'>indented   text</span></div>") is None
    assert html_to_markdown("<p>one</p><p>two</p>") is None


def test_paragraph_spacing_and_line_breaks():
    assert html_to_markdown("<p>one</p><p>two</p><p><b>three</b><br>four</p>") == "one\n\ntwo\n\n**three**\nfour"


def test_ordered_list_and_head_style_ignored():
    md = html_to_markdown("<head><style>b{x:y}</style><title>t</title></head><ol><li>a</li><li>b</li></ol><p>after</p>")
    assert md == "1. a\n1. b\nafter"


def test_word_fake_bullets_dropped():
    md = html_to_markdown("<p><b>Hi</b></p><p><span style='mso-list:Ignore'>·<span>&nbsp;&nbsp;</span></span>item</p>")
    assert md == "**Hi**\n\nitem"


def test_windows_cf_html_fragment():
    body = b"<html><body><!--StartFragment--><b>x</b><!--EndFragment--></body></html>"
    head = b"Version:0.9\r\nStartHTML:0000000105\r\nEndHTML:0000000200\r\nStartFragment:%010d\r\nEndFragment:%010d\r\n"
    hdr_len = len(head % (0, 0))
    s = hdr_len + body.index(b"<b>")
    e = hdr_len + body.index(b"<!--EndFragment")
    raw = (head % (s, e)) + body + b"\0"
    assert _cf_html_fragment(raw) == "<b>x</b>"


def test_formatter_output_round_trips_through_both_profiles():
    md = html_to_markdown(DOCS)
    for profile in ("docs", "exec"):
        acts = RichTextFormatter("win", profile).parse(md)
        typed = "".join(a.text for a in acts if isinstance(a, TypeAction))
        assert typed.replace("\n", "") == "Hello ProfessorI am writing about the deadline please nowFirstNestedSecondold new".replace("\n", "")
    ks = [a.shortcut for a in RichTextFormatter("win", "exec").parse(md) if isinstance(a, KeyAction)]
    assert "exec:formatBlock:<h1>" in ks and "exec:insertUnorderedList" in ks and "exec:strikeThrough" in ks
    assert "Control+b" in ks and "Control+i" in ks
