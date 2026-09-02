from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


DPI = 150
SCALE = DPI / 1440.0
PT_SCALE = DPI / 72.0
DOCX = Path("outputs/Predlojenie-komandirovka_BG_ICSQE-2026_formatted.docx")
OUT = Path("work/proxy_preview.png")
REG = r"C:\Windows\Fonts\times.ttf"
BOLD = r"C:\Windows\Fonts\timesbd.ttf"
ITALIC = r"C:\Windows\Fonts\timesi.ttf"


def font_for(p, default=9.2):
    run = next((r for r in p.runs if r.text), p.runs[0] if p.runs else None)
    size = float(run.font.size.pt) if run and run.font.size else default
    path = BOLD if run and run.bold else ITALIC if run and run.italic else REG
    return ImageFont.truetype(path, max(8, round(size * PT_SCALE)))


def wrap(draw, text, font, width):
    text = text or ""
    if not text:
        return [""]
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = word if not line else f"{line} {word}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def line_height(font):
    box = font.getbbox("Аgj")
    return max(10, box[3] - box[1] + 3)


def get_attr(el, name, default=0):
    if el is None:
        return default
    try:
        return int(el.get(qn(f"w:{name}"), default))
    except (TypeError, ValueError):
        return default


def cell_margins(cell):
    tcpr = cell._tc.get_or_add_tcPr()
    mar = tcpr.find(qn("w:tcMar"))
    if mar is None:
        return [60, 90, 60, 90]
    values = []
    for tag in ("top", "start", "bottom", "end"):
        values.append(get_attr(mar.find(qn(f"w:{tag}")), "w", 0))
    return values


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


doc = Document(DOCX)
sec = doc.sections[0]
W = round(sec.page_width.twips * SCALE)
H = round(sec.page_height.twips * SCALE)
left = round(sec.left_margin.twips * SCALE)
right = W - round(sec.right_margin.twips * SCALE)
top = round(sec.top_margin.twips * SCALE)
bottom = H - round(sec.bottom_margin.twips * SCALE)

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)
y = top

for block in iter_blocks(doc):
    if isinstance(block, Paragraph):
        font = font_for(block)
        pf = block.paragraph_format
        before = round((pf.space_before.pt if pf.space_before else 0) * PT_SCALE)
        after = round((pf.space_after.pt if pf.space_after else 1) * PT_SCALE)
        y += before
        lines = wrap(draw, block.text, font, right - left)
        lh = line_height(font)
        for line in lines:
            width = draw.textbbox((0, 0), line, font=font)[2]
            x = left
            if block.alignment == 1:
                x = left + ((right - left) - width) / 2
            elif block.alignment == 2:
                x = right - width
            draw.text((x, y), line, font=font, fill="black")
            y += lh
        y += after
        continue

    table = block
    grid = [int(c.get(qn("w:w"))) for c in table._tbl.tblGrid]
    col_px = [round(v * SCALE) for v in grid]
    for row in table.rows:
        cell_specs = []
        row_h = 0
        for cell, cw in zip(row.cells, col_px):
            mt, ms, mb, me = cell_margins(cell)
            mt, ms, mb, me = [round(v * SCALE) for v in (mt, ms, mb, me)]
            para_specs = []
            content_h = 0
            for p in cell.paragraphs:
                font = font_for(p)
                avail = max(10, cw - ms - me)
                lines = wrap(draw, p.text, font, avail)
                lh = line_height(font)
                before = round((p.paragraph_format.space_before.pt if p.paragraph_format.space_before else 0) * PT_SCALE)
                after = round((p.paragraph_format.space_after.pt if p.paragraph_format.space_after else 0) * PT_SCALE)
                para_specs.append((p, font, lines, lh, before, after))
                content_h += before + len(lines) * lh + after
            height = mt + content_h + mb
            row_h = max(row_h, height)
            cell_specs.append((cell, cw, mt, ms, mb, me, para_specs))
        x = left
        for cell, cw, mt, ms, mb, me, para_specs in cell_specs:
            tcpr = cell._tc.get_or_add_tcPr()
            shd = tcpr.find(qn("w:shd"))
            fill = shd.get(qn("w:fill")) if shd is not None else None
            if fill and fill not in ("auto", "FFFFFF"):
                draw.rectangle((x, y, x + cw, y + row_h), fill=f"#{fill}")
            yy = y + mt
            for p, font, lines, lh, before, after in para_specs:
                yy += before
                for line in lines:
                    tw = draw.textbbox((0, 0), line, font=font)[2]
                    tx = x + ms
                    if p.alignment == 1:
                        tx = x + (cw - tw) / 2
                    elif p.alignment == 2:
                        tx = x + cw - me - tw
                    draw.text((tx, yy), line, font=font, fill="black")
                    yy += lh
                yy += after
            borders = tcpr.find(qn("w:tcBorders"))
            if borders is not None:
                bottom_border = borders.find(qn("w:bottom"))
                if bottom_border is not None and bottom_border.get(qn("w:val"), "single") != "nil":
                    color = bottom_border.get(qn("w:color"), "D9D9D9")
                    draw.line((x, y + row_h, x + cw, y + row_h), fill=f"#{color}", width=1)
            x += cw
        y += row_h

draw.line((left, bottom, right, bottom), fill="#D00000", width=2)
draw.text((left, bottom + 4), f"usable-page boundary; content ends at y={y}, boundary={bottom}", font=ImageFont.truetype(REG, 12), fill="#D00000")
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"{OUT.resolve()}\ncontent_y={y}; boundary_y={bottom}; remaining_px={bottom-y}")
