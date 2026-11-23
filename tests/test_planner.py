"""Browser tests for Wood Cut Planner. Run with:  pytest -q   (see README for setup)."""
import re

from conftest import (BOOKSHELF, DOWNLOADS_STUB, NIGHTSTAND, NO_DOWNLOADS_STUB, furniture, make_state,
                      piece, plate)


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


# ---------------------------------------------------------------- layout basics

def test_example_loads_and_lays_out_everything(open_app):
    app = open_app().wait_done()          # no saved state -> built-in example
    assert app.errors == []
    placed, total = map(int, app.page.inner_text(".stat b >> nth=1").split("/"))
    assert placed == total > 0
    assert app.plates_needed() >= 1


def test_no_overlaps_and_pieces_stay_inside_usable_area(open_app):
    app = open_app(make_state([NIGHTSTAND, BOOKSHELF])).wait_done()
    trim_off, usable_l, usable_w = 100, 24200, 12000          # 1/100 cm units: trim 2 cm -> 1 cm each side
    for rects in app.boards():
        for i, a in enumerate(rects):
            assert a[0] >= trim_off - 1 and a[1] >= trim_off - 1
            assert a[0] + a[2] <= trim_off + usable_l + 1 and a[1] + a[3] <= trim_off + usable_w + 1
            for b in rects[i + 1:]:
                assert not overlaps(a, b)


def test_allowance_and_edge_trim_are_applied(open_app):
    app = open_app(make_state([furniture("Box", 1, [piece("Panel", 50, 30)])])).wait_done()
    meta = app.page.inner_text(".sheet-head .meta")
    assert "usable 242 × 120" in meta
    app.page.click(".sheet details summary")
    row = app.page.inner_text(".sheet tbody tr")
    assert "50×30" in row and "52×32" in row               # piece size and cut size (+2 cm)


def test_grain_locked_pieces_are_never_rotated(open_app):
    furn = furniture("Locked", 3, [piece("Strip", 100, 20, 3, rot=False), piece("Panel", 60, 40, 2, rot=False)])
    app = open_app(make_state([furn])).wait_done()
    titles = app.page.evaluate("[...document.querySelectorAll('svg.board g title')].map(t => t.textContent)")
    assert titles and not any("rotated" in t for t in titles)


def test_too_big_piece_is_reported_and_does_not_inflate_minimum(open_app):
    furn = furniture("Mixed", 1, [piece("Huge", 300, 50), piece("Small", 40, 30, 2)])
    app = open_app(make_state([furn])).wait_done()
    assert "larger than every plate" in app.page.inner_text(".warn")
    assert app.min_line().startswith("Minimum possible: 1")
    assert "✓" not in app.min_line()                       # not every piece placed -> no check mark


def test_every_piece_gets_a_label_or_letter(open_app):
    tiny = furniture("Tiny parts", 1, [piece("Dowel block", 3, 3, 6), piece("Spacer", 10, 2, 3),
                                       piece("Very long drawer runner name", 30, 5, 2), piece("פס תמיכה", 40, 3, 2)])
    app = open_app(make_state([NIGHTSTAND, tiny])).wait_done()
    r = app.page.evaluate("""() => { let unlabelled = 0, tags = 0;
        document.querySelectorAll('svg.board g').forEach(g => {
          if (g.querySelector('circle')) { tags++; return; }
          if (g.querySelector('rect') && !g.querySelector('text')) unlabelled++; });
        return { unlabelled, tags, keys: document.querySelectorAll('.key-i').length }; }""")
    assert r["unlabelled"] == r["tags"]                     # every piece without text has a letter tag
    assert r["tags"] > 0 and r["keys"] > 0


def _separable(rects):
    """True if the pieces can be cut apart with straight cuts that each run edge to edge."""
    if len(rects) <= 1:
        return True
    for axis in (0, 1):
        for c in sorted({r[axis] + r[axis + 2] for r in rects}):
            left = [r for r in rects if r[axis] + r[axis + 2] <= c]
            right = [r for r in rects if r[axis] >= c]
            if left and right and len(left) + len(right) == len(rects):
                return _separable(left) and _separable(right)
    return False


def test_straight_cut_mode_produces_guillotine_layouts(open_app):
    app = open_app(make_state([NIGHTSTAND, BOOKSHELF], mode="guillotine")).wait_done()

    def separable(rects):
        if len(rects) <= 1:
            return True
        for axis in (0, 1):
            cuts = sorted({r[axis] + r[axis + 2] for r in rects})
            for c in cuts:
                left = [r for r in rects if r[axis] + r[axis + 2] <= c]
                right = [r for r in rects if r[axis] >= c]
                if left and right and len(left) + len(right) == len(rects):
                    return separable(left) and separable(right)
        return False

    for rects in app.boards():
        assert separable(rects), "a plate needs a cut that does not run edge to edge"


def test_straight_cut_mode_stays_straight_on_many_random_sets(open_app):
    """Regression: joining leftover spaces once produced layouts needing a cut that isn't edge to edge."""
    import random
    rnd = random.Random(11)
    for _ in range(12):
        pcs = [piece(f"P{i}", rnd.randint(20, 150), rnd.randint(5, 60), rnd.randint(1, 4), rot=rnd.random() < .8) for i in range(rnd.randint(4, 9))]
        pcs = [dict(p, W=min(p["W"], p["L"])) for p in pcs]
        app = open_app(make_state([furniture("R", rnd.randint(1, 3), pcs)], mode="guillotine")).wait_done()
        for rects in app.boards():
            assert _separable(rects), "a plate needs a cut that does not run edge to edge"


def test_unticked_piece_is_left_out(open_app):
    furn = dict(furniture("Desk", 1, [piece("Top", 120, 60), piece("Leg panel", 70, 55, 2), dict(piece("Modesty panel", 100, 30), on=False)]), open=True)
    app = open_app(make_state([furn])).wait_done()
    placed, total = map(int, app.page.inner_text(".stat b >> nth=1").split("/"))
    assert placed == total == 3                                # the unticked panel is not counted
    titles = " ".join(app.page.evaluate("[...document.querySelectorAll('svg.board g title')].map(t => t.textContent)"))
    assert "Modesty panel" not in titles and "Top" in titles
    assert "1 left out" in app.page.inner_text(".furn-foot")
    assert "off" in app.page.get_attribute(".furn .row.piece:not(.head) >> nth=2", "class")
    # ticking it again brings it back
    app.page.check(".furn .row.piece:not(.head) >> nth=2 >> input[data-k=on]")
    app.page.wait_for_function("[...document.querySelectorAll('.stat b')][1]?.textContent === '4/4'", timeout=20000)
    assert "off" not in app.page.get_attribute(".furn .row.piece:not(.head) >> nth=2", "class")


# ---------------------------------------------------------------- minimum possible plates

NIGHTSTAND_BASE = furniture("Nightstand Base", 2, [
    piece("Top edge", 50, 13.5, 2, rot=False), piece("Top middle", 50, 13, 1, rot=False),
    piece("Shelf part", 41, 12, 3, rot=False), piece("Leg", 48, 4, 4), piece("Stretcher", 42, 4, 2)])


def drawer(build):
    return furniture("Nightstand Drawer", build, [
        piece("Side_ext", 28, 12, 2), piece("Back_ext", 42, 12), piece("Front", 41, 12), piece("Side_int", 28, 8, 2),
        piece("Back_int", 40, 8), piece("Bottom edge", 42, 10, 2), piece("Bottom middle", 42, 8)])


def test_narrow_boards_reach_the_true_minimum(open_app):
    boards = [plate(290, 19)]
    app = open_app(make_state([NIGHTSTAND_BASE, drawer(1)], plates=boards, effort="normal")).wait_done()
    assert app.plates_needed() == 5 and app.min_line() == "Minimum possible: 5 ✓"
    app = open_app(make_state([NIGHTSTAND_BASE, drawer(2)], plates=boards, effort="normal")).wait_done()
    assert app.plates_needed() == 6 and app.min_line() == "Minimum possible: 6 ✓"


def test_minimum_respects_plate_quantities(open_app):
    furn = furniture("Panels", 1, [piece("Panel", 100, 50, 9)])       # 9 x (102x52) cm
    unlimited = open_app(make_state([furn], plates=[plate(244, 122)])).wait_done()
    limited = open_app(make_state([furn], plates=[plate(244, 122, qty="1"), plate(120, 60, name="Small")])).wait_done()
    lo_unlimited = int(re.search(r"\d+", unlimited.min_line()).group())
    lo_limited = int(re.search(r"\d+", limited.min_line()).group())
    assert lo_limited > lo_unlimited                          # only one big plate -> more small plates needed
    assert limited.plates_needed() >= lo_limited


def test_search_more_button_when_minimum_not_reached(open_app):
    app = open_app(make_state([NIGHTSTAND, dict(BOOKSHELF, qty=2)])).wait_done()
    if "✓" in app.min_line():
        return                                                # reached the minimum: nothing to offer
    assert app.page.is_visible("#moreBtn")
    app.page.click("#moreBtn")
    app.page.wait_for_selector(".search.busy", timeout=3000)


# ---------------------------------------------------------------- totals

def test_area_volume_and_price_totals(open_app):
    st = make_state([NIGHTSTAND, BOOKSHELF], plates=[plate(244, 122, T="3/4", P="4500")], currency="$")
    app = open_app(st).wait_done()
    n = app.plates_needed()
    area = n * 2.44 * 1.22
    assert app.stat(4).startswith(f"{area:.2f}")
    assert app.stat(5).startswith(f"{area * 0.75 * 0.0254:.3f}")
    assert app.page.inner_text(".stat.price b") == f"${area * 0.75 * 0.0254 * 4500:,.2f}"


def test_thickness_accepts_fractions(open_app):
    app = open_app(make_state([NIGHTSTAND], plates=[plate(244, 122, T="1 1/2")])).wait_done()
    vol = float(app.page.inner_text(".stat b >> nth=5"))
    assert abs(vol - app.plates_needed() * 2.44 * 1.22 * 1.5 * 0.0254) < 0.002


def test_missing_thickness_or_price_shows_dash(open_app):
    app = open_app(make_state([NIGHTSTAND], plates=[plate(244, 122)])).wait_done()
    assert app.page.inner_text(".stat b >> nth=5") == "—"
    assert app.page.inner_text(".stat.price b") == "—"


# ---------------------------------------------------------------- furniture CSV

def test_furniture_csv_round_trip(open_app, tmp_path):
    named = dict(NIGHTSTAND, name='שידת לילה, "דגם A"', pieces=NIGHTSTAND["pieces"][:-1] + [dict(NIGHTSTAND["pieces"][-1], on=False)])
    app = open_app(make_state([named, BOOKSHELF]), stub=DOWNLOADS_STUB).wait_done()
    before = app.page.evaluate("JSON.stringify(JSON.parse(localStorage.getItem('woodcut-planner-v1')).furniture.map(f => [f.name, String(f.qty), f.pieces.map(p => [p.name, String(p.L), String(p.W), String(p.qty), p.rot, p.on !== false])]))")
    app.page.click("#exportFurn")
    app.page.wait_for_function("Object.keys(window.__saved).some(k => k.startsWith('furniture'))")
    csv = next(v for k, v in app.saved().items() if k.startswith("furniture"))
    f = tmp_path / "furniture.csv"
    f.write_bytes(csv)
    app.page.click("#clearBtn")
    app.page.set_input_files("#furnFile", str(f))
    app.page.click("[data-imp=replace]")
    after = app.page.evaluate("JSON.stringify(JSON.parse(localStorage.getItem('woodcut-planner-v1')).furniture.map(f => [f.name, String(f.qty), f.pieces.map(p => [p.name, String(p.L), String(p.W), String(p.qty), p.rot, p.on !== false])]))")
    assert before == after


def test_import_hebrew_headers_semicolons_and_decimal_commas(open_app, tmp_path):
    f = tmp_path / "he.csv"
    f.write_text("רהיט;כמות רהיטים;חלק;אורך;רוחב;כמות;סיבוב\nכיסא;4;מושב;40;40;1;כן\nכיסא;4;רגל;45;4,5;4;לא\n", encoding="utf-8")
    app = open_app(make_state([NIGHTSTAND])).wait_done()
    app.page.set_input_files("#furnFile", str(f))
    app.page.click("[data-imp=add]")
    last = app.page.evaluate("JSON.parse(localStorage.getItem('woodcut-planner-v1')).furniture.slice(-1)[0]")
    assert last["name"] == "כיסא" and str(last["qty"]) == "4"
    assert last["pieces"][1] == {"name": "רגל", "L": "45", "W": "4.5", "qty": "4", "rot": False, "on": True}


# ---------------------------------------------------------------- exports

def test_exports_inside_claude(open_app):
    app = open_app(make_state([NIGHTSTAND, BOOKSHELF], plates=[plate(244, 122, T="3/4", P="4500")]), stub=DOWNLOADS_STUB).wait_done()
    app.page.click("#pdfBtn")
    app.page.wait_for_function("Object.keys(window.__saved).some(k => k.endsWith('.pdf'))", timeout=30000)
    app.page.click("#csvBtn")
    app.page.wait_for_function("Object.keys(window.__saved).some(k => k.startsWith('cut-list'))")
    files = app.saved()
    pdf = next(v for k, v in files.items() if k.endswith(".pdf"))
    assert pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type /Page(?!s)", pdf)) >= 1 + app.plates_needed()   # summary + one page per plate
    csv = next(v for k, v in files.items() if k.startswith("cut-list")).decode("utf-8-sig")
    assert csv.splitlines()[0].startswith("Plate,Plate type,Thickness (in),Plate price,Furniture,Unit,Piece")
    assert app.errors == []


def test_exports_in_shared_view_fall_back_to_on_screen(open_app):
    app = open_app(make_state([NIGHTSTAND]), stub=NO_DOWNLOADS_STUB, in_frame=True).wait_done()
    app.page.click("#pdfBtn")
    app.page.wait_for_selector(".modal-page", timeout=30000)
    assert app.page.locator(".modal-page").count() >= 2
    app.page.click("#modalClose")
    app.page.click("#csvBtn")
    assert app.page.input_value(".modal-text").startswith("Plate,")


def test_exports_as_standalone_website_download_files(open_app):
    app = open_app(make_state([NIGHTSTAND])).wait_done()
    for button, ext in (("#pdfBtn", ".pdf"), ("#csvBtn", ".csv"), ("#exportFurn", ".csv")):
        with app.page.expect_download(timeout=30000) as d:
            app.page.click(button)
        assert d.value.suggested_filename.endswith(ext)


# ---------------------------------------------------------------- phone layout

def test_phone_layout_has_no_horizontal_scroll(open_app):
    app = open_app(make_state([NIGHTSTAND, BOOKSHELF], plates=[plate(244, 122, T="3/4", P="4500")]), viewport=(390, 800)).wait_done()
    assert not app.page.evaluate("document.documentElement.scrollWidth > window.innerWidth")


# ---------------------------------------------------------------- sections mode

def _sections(app):
    return app.page.evaluate("""() => [...document.querySelectorAll('svg.board')].map(s => ({
        rects: [...s.querySelectorAll('g rect[stroke-dasharray]')].map(r => ['x','y','width','height'].map(a => +r.getAttribute(a))),
        cuts: [...s.querySelectorAll('line')].map(l => +l.getAttribute('x1')) }))""")


def test_sections_keep_every_piece_inside_one_section(open_app):
    st = make_state([NIGHTSTAND_BASE, drawer(1)], plates=[plate(290, 19)], sections=True, sectionLen=100, effort="normal")
    app = open_app(st).wait_done()
    assert app.plates_needed() == 5                                   # same as without sections for these boards
    for d in _sections(app):
        for r in d["rects"]:
            for c in d["cuts"]:
                assert not (r[0] < c - 1 and r[0] + r[2] > c + 1), "a piece crosses a section cut"
    for line in app.page.locator(".secline").all_inner_texts():
        lens = [float(x) for x in re.search(r": ([\d. +]+) cm", line).group(1).split(" + ")]
        assert all(l <= 100 for l in lens)


def test_section_cut_lines_run_past_the_plate_edges(open_app):
    app = open_app(make_state([NIGHTSTAND_BASE, drawer(1)], plates=[plate(290, 19)], sections=True, sectionLen=100)).wait_done()
    ys = app.page.evaluate("[...document.querySelectorAll('svg.board line')].map(l => [+l.getAttribute('y1'), +l.getAttribute('y2'), l.getAttribute('stroke')])")
    assert ys and all(y1 < 0 and y2 > 1900 and stroke == "#111" for y1, y2, stroke in ys)   # plate width is 19 cm = 1900 units


def test_piece_longer_than_section_is_reported(open_app):
    st = make_state([BOOKSHELF], plates=[plate(244, 122)], sections=True, sectionLen=100)
    app = open_app(st).wait_done()
    assert "longer than the 100 cm section limit" in app.page.inner_text(".warn")
    lo = int(re.search(r"\d+", app.min_line()).group())
    assert lo <= app.plates_needed()                                   # the long sides don't inflate the minimum


def test_sections_column_in_csv(open_app):
    st = make_state([NIGHTSTAND], plates=[plate(244, 122)], sections=True, sectionLen=100)
    app = open_app(st, stub=DOWNLOADS_STUB).wait_done()
    app.page.click("#csvBtn")
    app.page.wait_for_function("Object.keys(window.__saved).some(k => k.startsWith('cut-list'))")
    rows = next(v for k, v in app.saved().items() if k.startswith("cut-list")).decode("utf-8-sig").splitlines()
    assert rows[0].endswith(",Rotated,Section")
    assert all(r.rsplit(",", 1)[1].isdigit() for r in rows[1:])


# ---------------------------------------------------------------- keep furniture together

def _plates_per_unit(app):
    app.page.click("#csvBtn")
    app.page.wait_for_function("Object.keys(window.__saved).some(k => k.startsWith('cut-list'))")
    import csv, io
    rows = list(csv.DictReader(io.StringIO(next(v for k, v in app.saved().items() if k.startswith("cut-list")).decode("utf-8-sig"))))
    units = {}
    for r in rows:
        units.setdefault((r["Furniture"], r["Unit"]), set()).add(r["Plate"])
    return sorted(len(v) for v in units.values())


def test_keep_together_puts_each_unit_on_one_plate(open_app):
    st = make_state([NIGHTSTAND, BOOKSHELF], plates=[plate(244, 122)], group=True, effort="normal")
    app = open_app(st, stub=DOWNLOADS_STUB).wait_done()
    assert app.plates_needed() == 3                                   # grouping never costs extra plates here
    assert _plates_per_unit(app) == [1, 1, 1]
    assert "Every unit is on its fewest possible plates" in app.page.inner_text(".units")
    labels = " ".join(app.page.evaluate("[...document.querySelectorAll('svg.board text')].map(t => t.textContent)"))
    assert "①" in labels and "②" in labels                            # unit numbers on the nightstand pieces


def test_keep_together_on_narrow_boards_with_sections(open_app):
    st = make_state([NIGHTSTAND_BASE, drawer(2)], plates=[plate(290, 19)], group=True, sections=True, effort="normal")
    app = open_app(st, stub=DOWNLOADS_STUB).wait_done()
    assert app.plates_needed() == 6
    assert max(_plates_per_unit(app)) <= 3                            # each unit needs at least 2 boards; allow one extra
    for d in _sections(app):                                          # sections rules still hold
        for r in d["rects"]:
            for c in d["cuts"]:
                assert not (r[0] < c - 1 and r[0] + r[2] > c + 1)


def test_without_keep_together_layout_still_uses_fewest_plates(open_app):
    a = open_app(make_state([NIGHTSTAND, BOOKSHELF], effort="normal")).wait_done().plates_needed()
    b = open_app(make_state([NIGHTSTAND, BOOKSHELF], effort="normal", group=True)).wait_done().plates_needed()
    assert b == a
