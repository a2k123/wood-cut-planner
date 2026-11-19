"""Shared helpers for the Wood Cut Planner browser tests.

The app is a single index.html, so every test opens it in headless Chromium with a
prepared state in localStorage and inspects the rendered page.
"""
import base64
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "index.html").as_uri()

# Optional local copy of jsPDF (set JSPDF_PATH) so PDF tests work offline; otherwise it loads from cdnjs.
JSPDF_PATH = os.environ.get("JSPDF_PATH")

# Stand-in for Claude's "downloads" capability: records saved files instead of downloading them.
DOWNLOADS_STUB = """
window.__saved = {};
window.claude = { use: async (n) => n === 'downloads' ? { save: async ({filename, data}) => {
  let b64;
  if (typeof data === 'string') b64 = btoa(unescape(encodeURIComponent(data)));
  else { const u = new Uint8Array(data); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); b64 = btoa(s); }
  window.__saved[filename] = b64; return { status: 'saved' }; } } : null };
"""
NO_DOWNLOADS_STUB = "window.claude = { use: async () => null };"


def piece(name, L, W, qty=1, rot=True):
    return {"name": name, "L": L, "W": W, "qty": qty, "rot": rot}


def furniture(name, qty, pieces):
    return {"name": name, "qty": qty, "open": False, "pieces": pieces}


def plate(L=244, W=122, qty="", name="Ply", T="", P=""):
    return {"name": name, "L": L, "W": W, "T": T, "qty": qty, "P": P}


def make_state(furn, plates=None, **settings):
    st = {"allowance": 2, "trim": 2, "kerf": 0, "mode": "free", "effort": "quick", "currency": "₪",
          "plates": plates or [plate()], "furniture": furn}
    st.update(settings)
    return st


NIGHTSTAND = furniture("Nightstand", 2, [
    piece("Top", 60, 45), piece("Side", 55, 40, 2), piece("Shelf", 52, 38, 2), piece("Back", 52, 50),
    piece("Drawer front", 48, 14, rot=False), piece("Drawer side", 36, 12, 2), piece("Rail", 52, 6, 4),
])
BOOKSHELF = furniture("Bookshelf", 1, [
    piece("Side", 180, 30, 2, rot=False), piece("Top", 80, 30), piece("Shelf", 76, 28, 4), piece("Kick", 76, 8),
])


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


class App:
    """A page with the planner open, plus small helpers to read results."""

    def __init__(self, page, errors):
        self.page, self.errors = page, errors

    def wait_done(self, timeout=20000):
        self.page.wait_for_selector(".search.done", timeout=timeout)
        return self

    def stat(self, i):
        return self.page.inner_text(f".stat >> nth={i}")

    def plates_needed(self):
        return int(self.page.inner_text(".stat b >> nth=0"))

    def min_line(self):
        return self.page.inner_text(".minline")

    def boards(self):
        """Per plate: list of [x, y, w, h] cut-size rectangles (allowance included)."""
        return self.page.evaluate("""() => [...document.querySelectorAll('svg.board')].map(s =>
            [...s.querySelectorAll('g rect[stroke-dasharray]')].map(r => ['x','y','width','height'].map(a => +r.getAttribute(a))))""")

    def saved(self):
        return {k: base64.b64decode(v) for k, v in self.page.evaluate("window.__saved || {}").items()}


@pytest.fixture
def open_app(browser, tmp_path):
    pages = []

    def _open(state=None, stub=None, viewport=(1280, 900), in_frame=False):
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("https://fonts.googleapis.com/**", lambda r: r.abort())
        if JSPDF_PATH:
            page.route("https://cdnjs.cloudflare.com/**",
                       lambda r: r.fulfill(path=JSPDF_PATH, content_type="application/javascript"))
        init = ""
        if stub:
            init += stub
        if state is not None:
            init += "localStorage.setItem('woodcut-planner-v1', %s);" % json.dumps(json.dumps(state))
        if init:
            page.add_init_script(init)
        url = INDEX
        if in_frame:
            frame_html = tmp_path / "frame.html"
            frame_html.write_text(f'<!DOCTYPE html><iframe src="{INDEX}" style="width:100%;height:900px;border:0"></iframe>')
            url = frame_html.as_uri()
        page.goto(url)
        pages.append(page)
        target = page.frames[1] if in_frame else page
        if in_frame:
            target.wait_for_selector("#results")
        return App(target, errors)

    yield _open
    for p in pages:
        p.close()
