# 🪵 Wood Cut Planner

**Plan your cuts before you touch the saw.** Describe your furniture and your boards or sheets, and Wood Cut Planner lays every piece out on as few plates as possible. It tells you what the material will cost and gives you a printable cut plan.

**▶ Live site: https://a2k123.github.io/wood-cut-planner/**  ·  Preview of upcoming changes: [/dev/](https://a2k123.github.io/wood-cut-planner/dev/)

![Wood Cut Planner showing furniture inputs on the left and a packed plywood sheet on the right](docs/screenshot.png)

---

## Features

### Plan by furniture
- **Furniture with parts:** define a nightstand, a bookshelf or a stool with its pieces, then set **Build** to how many of each you want. The planner multiplies everything out for you.
- **Furniture cards:** collapse, duplicate or delete each card. Deleting asks you to confirm first.
- **Grain direction:** untick **Rot** on a piece to keep its length along the plate's length.
- **Use checkbox:** untick a piece to leave it out of the layout without deleting it, for example a part you already have. It stays in the list, grayed out, and the card shows how many are left out.

### Plates
- **Several plate sizes:** add as many plate types as you like, each with a name, length, width and quantity. Leave the quantity blank for unlimited.
- **Thickness in inches:** type it the way woodworkers write it: `3/4`, `1 1/2`, `1-1/2`, `5/8"` or `0.75`.
- **Price per m³:** set a price for each plate type.

### Real-world waste
- **Edge trim:** every plate loses a strip when you straighten its edges. The default is 2 cm off the length and the width, and only the usable area is packed.
- **Allowance:** a margin added to each piece's length and width, 2 cm by default, so you can trim to final size.
- **Saw kerf:** an optional gap for the width of the blade.

### Smart arrangement
- **Two layout styles:**
  - **Tightest fit:** any arrangement that saves the most material.
  - **Straight through-cuts only:** every cut runs edge to edge, which is what a table saw or panel saw needs.
- **Cut plates into sections first:** optional. Each plate is first cut across its length into sections no longer than a limit you set (1 m by default), so long boards are easier to carry and handle. Every piece stays inside one section. The sketch marks the section cuts with **black dotted lines that run past the plate's edges** and labels each section's length. If a piece is longer than the limit, you're told so.
- **Keep furniture together:** optional. Among the layouts with the fewest plates, the planner prefers the one where each unit's pieces (for example nightstand ②) share a plate and sit close together, and each piece of furniture uses as few plates as possible. Identical pieces are swapped between units to line them up. Pieces show their unit number (①, ②…), and a summary lists each unit's plates (and sections), with ✓ when a unit is on its fewest possible plates. This mode never uses extra plates.
- **Background search:** the planner keeps looking for a better layout without freezing the page, and redraws whenever it finds one. Choose **Quick** (under half a second), **Normal** (up to 3 seconds) or **Thorough** (up to 10 seconds).
- **Live progress:** a status line shows the search time and the number of layouts tried.
- **Search 10 s more:** a button that appears when the minimum wasn't reached.
- **Minimum possible plates:** no layout can use fewer plates than this number. It counts total area, how many of each plate you have, and, on narrow boards, which pieces can actually sit side by side. A ✓ appears when your layout reaches it.

### Results
- **Totals:** plates needed, pieces placed, material used and offcut (m²).
- **Plate area, volume and price:** total plate area (m²), total plate volume (m³) and **total price**, using each plate's volume × its price per m³. You choose the currency symbol (₪ by default).
- **Clear drawings:** each plate shows the real piece (solid), the allowance (striped band), the edge trim (hatched frame) and the usable offcut.
- **Labels on every piece:** pieces too small for a label get a letter. A key under the plate explains each letter, and identical small pieces share one letter.
- **Warnings:** you're told when a piece is bigger than every plate, only fits if rotated, or when you've run out of plates.

### Exports and saving
| Button | What you get |
|---|---|
| **Export PDF** | An A4 landscape cut plan. Page 1 has a summary with all the totals and a full parts list. Then there is one page per plate with its sketch, letter key and pieces. |
| **Export CSV** | One row per piece: plate, thickness, plate price, furniture, unit, piece, real size, cut size, position, rotation, section. It opens in Excel and Google Sheets. |
| **Copy text** | A plain-text cut list for pasting into a message. |
| **Save furniture as CSV** | Your furniture designs, so you can keep your work or share it. |
| **Import furniture CSV** | Load saved designs, replacing what you have or adding to it. |

- **Hebrew and other right-to-left names** display correctly on screen, in the PDF and in Excel.
- **Shared views:** in a shared Claude view, where downloads aren't allowed, the PDF opens as page images you can save and the CSV opens as text you can copy.
- **Phones:** the layout works on phone screens.

### Units
All sizes are in **centimetres**. Areas are in **m²**, volumes in **m³**. Plate **thickness** is the one exception: it's in **inches**.

## Furniture CSV format

Each row is one piece. Rows with the same furniture name are grouped together.

```csv
Furniture,Build,Piece,Length (cm),Width (cm),Qty,Can rotate,Include
Nightstand,2,Top,60,45,1,yes,yes
Nightstand,2,Side,55,40,2,yes,yes
Nightstand,2,Drawer front,48,14,1,no,yes
Bookshelf,1,Side,180,30,2,no,yes
Bookshelf,1,Shelf,76,28,4,yes,no
```

- **Build** is how many of that furniture to make. **Qty** is per one piece of furniture.
- **Include** is `yes` or `no`, matching the Use checkbox. If the column is missing, every piece is included, so older files still work.
- Commas or semicolons both work, so Excel files from any region import fine. Decimal commas (`4,5`) work too.
- Hebrew column headers are recognized: `רהיט, כמות רהיטים, חלק, אורך, רוחב, כמות, סיבוב`.

## How it works

The whole app is a single `index.html` file, with no build step and no server.

- **Packing:** two methods are used.
  - **Tightest fit** uses the *MaxRects* method.
  - **Straight through-cuts** uses a *guillotine* method, which splits the remaining space in two after every cut. Tightest fit also tries guillotine layouts, because they're valid there too.
- **Search:** the planner tries many piece orders and placement rules. It then keeps improving the best one with small changes, and tries to fit everything on one plate fewer by spreading pieces across a fixed set of plates. It keeps the layout that uses the fewest plates, then the least material. Among equal options, it prefers the one that leaves one large usable offcut.
- **Minimum:** on narrow boards, a small linear program over the ways pieces can stack across the width gives the true least board length needed.
- **Drawing:** plates are drawn as SVG.
- **PDF:** pages are drawn on a canvas, so right-to-left text always renders correctly, then packed into a PDF with [jsPDF](https://github.com/parallax/jsPDF).
- **Privacy:** your data stays in your browser's local storage. Nothing is uploaded anywhere.

## Run it locally

Download `index.html` and open it in any modern browser. That's it.

To host your own copy, put `index.html` on any static host, such as GitHub Pages, Netlify or Cloudflare Pages.

## Tests

Browser tests in `tests/` open the page in headless Chromium and check:
- layouts have no overlaps and pieces stay inside the usable area
- the allowance and edge trim are applied, and grain-locked pieces never rotate
- every piece gets a label or a letter, and unticked pieces are left out
- straight-cut mode really produces edge-to-edge cuts, including on many random sets
- in sections mode, no piece crosses a section cut, sections respect the length limit, and the cut lines run past the plate's edges
- keep-together mode puts each unit on its fewest plates without using extra plates
- the minimum is correct for narrow boards and respects plate quantities
- the area, volume and price totals are right, and inch fractions are read correctly
- furniture CSV round-trips, and imports with Hebrew headers, semicolons and decimal commas work
- PDF and CSV exports work inside Claude, in a shared view and as a normal website
- the phone layout doesn't scroll sideways

Run them:

```bash
pip install pytest playwright
python -m playwright install chromium
python -m pytest -q
```

They also run automatically on GitHub for every push (see the **Actions** tab).

## Branches

| Branch | What it is |
|---|---|
| `prod` | The live site at the main address. |
| `dev` | The preview at `/dev/`, for trying changes before they go live. |
| `main` | The default branch, kept in step with `prod`. |
| `gh-pages` | Built automatically from `prod` and `dev`. Don't edit it by hand. |

## Feedback

Found a bug or have an idea? [Open an issue](https://github.com/a2k123/wood-cut-planner/issues). Suggestions from people who actually cut wood are especially welcome.
