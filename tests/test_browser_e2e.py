"""Real-Chrome tests (skipped when Playwright's Chromium isn't installed or there is no
display). They start Chrome with the same flags FlowState launches it with and drive it
through PlaywrightDriver over CDP, exactly like the app does."""
import json, os, subprocess, sys, tempfile, time, urllib.request
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
pw_api = pytest.importorskip("playwright.sync_api")
from os_layer.playwright_driver import PlaywrightDriver, CHROME_FLAGS

PORT = 9337
# A TinyMCE-like editor: contenteditable body inside an iframe (this is how Canvas's
# rich content editor is built), plus a plain textarea (Canvas Inbox style).
EDITOR_PAGE = """<title>%s</title>
<textarea id=ta></textarea>
<iframe id=ed srcdoc="<body contenteditable=true id=b></body>" width=400 height=200></iframe>"""


def url(title):
    return "data:text/html," + urllib.request.quote(EDITOR_PAGE % title)


@pytest.fixture(scope="module")
def chrome():
    with pw_api.sync_playwright() as p:
        exe = p.chromium.executable_path
        if not os.path.exists(exe):
            pytest.skip("Playwright Chromium not installed (playwright install chromium)")
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            pytest.skip("needs a display (run under xvfb-run)")
        prof = tempfile.mkdtemp()
        proc = subprocess.Popen([exe, f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
                                 "--no-sandbox", *CHROME_FLAGS, "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://localhost:{PORT}/json/version")
                break
            except Exception:
                time.sleep(0.25)
        yield p
        proc.terminate()


@pytest.fixture
def drv(chrome):
    d = PlaywrightDriver(chrome, port=PORT)
    yield d
    d.detach()


def open_tab(drv, title):
    """A new tab in the SAME window as the others, like a user pressing Ctrl+T."""
    d = PlaywrightDriver(drv.p, port=PORT)
    d._connect()
    ctx = d.browser.contexts[0]
    known = set(id(pg) for pg in ctx.pages)
    with ctx.expect_page() as info:
        d.browser.new_browser_cdp_session().send("Target.createTarget", {"url": url(title), "newWindow": False})
    page = info.value
    page.wait_for_load_state()
    d.browser = None  # keep the connection alive; only used to open the tab
    return page


def front_title():
    """Chrome lists the active tab first. (Playwright can't tell: it makes background
    tabs report visibilityState=visible via focus emulation.)"""
    tabs = [t for t in json.loads(urllib.request.urlopen(f"http://localhost:{PORT}/json/list").read())
            if t["type"] == "page"]
    return tabs[0]["title"]


def focus_editor(page, which="b"):
    page.bring_to_front()
    if which == "ta":
        page.click("#ta")
    else:
        page.frame_locator("#ed").locator("#b").click()


def editor_html(page):
    return page.frame_locator("#ed").locator("#b").inner_html()


def test_types_into_pinned_tab_after_user_switches_away(drv):
    a = open_tab(drv, "Canvas Mail A")
    focus_editor(a)
    drv.attach("Canvas Mail A - Google Chrome")
    assert drv.page.title() == "Canvas Mail A"
    b = open_tab(drv, "Some other tab")
    b.bring_to_front()                       # user navigates away
    time.sleep(0.3)
    assert front_title() == "Some other tab"
    for ch in "hello":
        drv.send_char(ch, 0.01)
    assert front_title() == "Some other tab"  # typing must not pull tab A forward
    assert editor_html(a) == "hello"
    assert b.frame_locator("#ed").locator("#b").inner_html() == ""


def test_pin_survives_pause_and_navigation(drv):
    """Old behaviour: pause detached, resume re-picked whatever tab was visible."""
    a = open_tab(drv, "Pinned A")
    focus_editor(a)
    drv.attach("Pinned A - Google Chrome")
    pinned = drv.page
    b = open_tab(drv, "Other B")
    focus_editor(b)                          # user is now in B and focus is in B's editor
    drv.attach()                             # what resume does: must be a no-op
    assert drv.page is pinned
    drv.send_char("x", 0.01)
    assert editor_html(a) == "x" and editor_html(b) == ""


def test_title_match_prefers_visible_duplicate_and_ignores_empty_titles(drv):
    a = open_tab(drv, "Same Title")
    b = open_tab(drv, "Same Title")
    a.bring_to_front()
    drv.attach("Same Title - Google Chrome")
    assert drv.page.url == a.url
    drv.detach()
    blank = drv.p.chromium.connect_over_cdp(f"http://localhost:{PORT}").contexts[0].new_page()
    blank.goto("about:blank")                 # empty title must not match everything
    b.bring_to_front()
    drv.attach("Same Title - Google Chrome")
    assert drv.page.title() == "Same Title"


def test_focused_kind_and_exec_command_in_iframe_editor(drv):
    a = open_tab(drv, "Kinds")
    focus_editor(a, "ta")
    drv.attach("Kinds - Google Chrome")
    assert drv.focused_kind() == "plain"
    focus_editor(a, "b")
    assert drv.focused_kind() == "rich"
    drv.send_char("a", 0.01)
    drv.exec_command("insertUnorderedList")
    drv.send_char("b", 0.01)
    drv.exec_command("strikeThrough")
    drv.send_char("c", 0.01)
    html = editor_html(a)
    assert "<ul>" in html and "<li>" in html
    assert "<strike>c</strike>" in html or "<s>c</s>" in html


def test_exec_command_works_in_background_tab(drv):
    a = open_tab(drv, "BG exec")
    focus_editor(a)
    drv.attach("BG exec - Google Chrome")
    open_tab(drv, "front").bring_to_front()
    time.sleep(0.3)
    assert front_title() == "front"
    drv.exec_command("formatBlock", "<h2>")
    drv.send_char("T", 0.01)
    assert "<h2>T</h2>" in editor_html(a)


# ─── Full engine runs (TypingEngine -> PlaywrightDriver -> real Chrome) ──────────

import threading
import engine as engine_mod
from engine import TypingEngine

FAST = dict(UserMeanDelay=10, UserVariance=2, EnableTypos=0, EnableRevisions=0, TypoChance=0,
            EnableBrainstormPauses=0, EnableSemanticSpeed=0, EnableClausePauses=0,
            EnableChunkBurst=0, EnableSmartRevisions=0, EnableEntityCare=0,
            SentencePauseMs=0, ParagraphPauseMs=0, EnableRichText=1)
HTML = "<h1>Hi</h1><p>Some <b>bold</b> text</p><ul><li>one</li><li>two</li></ul>"


@pytest.fixture
def make_engine(chrome, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(engine_mod, "get_clipboard_html", lambda: None)
    made = []

    def make(clip, html=None, **settings):
        monkeypatch.setattr(engine_mod, "get_clipboard_html", lambda: html)
        drv = PlaywrightDriver(chrome, port=PORT)
        drv.get_clipboard = lambda: clip
        e = TypingEngine(drv)
        e.settings.update(FAST, **settings)
        made.append(drv)
        return e
    yield make
    for d in made:
        d.detach()


def test_engine_full_run_formats_and_survives_navigating_away_and_pausing(chrome, make_engine):
    drv0 = PlaywrightDriver(chrome, port=PORT)
    a = open_tab(drv0, "Canvas Compose")
    focus_editor(a)
    b = open_tab(drv0, "Library search")
    e = make_engine("Hi\nSome bold text\none\ntwo", html=HTML)

    calls = {"n": 0}
    real_sleep = e._sleep

    def sleep(d):
        calls["n"] += 1
        if calls["n"] == 60:                 # mid-run: user pauses, goes to another tab, clicks in it
            e.set_state(paused=True)
            focus_editor(b)
            threading.Timer(0.4, lambda: e.set_state(paused=False)).start()
        real_sleep(0.0 if calls["n"] < 60 and calls["n"] > 5 else d)   # keep countdown, skip the rest
    e._sleep = sleep

    b.bring_to_front()                       # user is already looking at another tab when typing starts
    e.trigger_typing("Canvas Compose - Google Chrome")

    assert calls["n"] > 60                   # the pause + tab switch really happened mid-run
    html = editor_html(a)
    assert "<h1>Hi</h1>" in html
    assert "<b>bold</b>" in html
    assert "<ul><li>one</li><li>two</li></ul>" in html
    assert editor_html(b) == ""              # nothing leaked into the tab the user moved to
    assert front_title() == "Library search"  # and the tab was never pulled forward
    assert e.is_running is False


def test_engine_plain_textarea_gets_text_verbatim(chrome, make_engine):
    drv0 = PlaywrightDriver(chrome, port=PORT)
    a = open_tab(drv0, "Canvas Inbox")
    focus_editor(a, "ta")
    e = make_engine("- keep *these* markers\nsecond line", html="<ul><li>ignored</li></ul>")
    e._sleep = lambda d: None
    e.trigger_typing("Canvas Inbox - Google Chrome")
    assert a.input_value("#ta") == "- keep *these* markers\nsecond line"
