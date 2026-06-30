#!/usr/bin/env python3
"""
Converte Doc-Tecnica-FarmacoMatch.md em PDF estilizado.
Usa o parser markdown (biblioteca markdown) + reportlab com fontes DejaVu
(suporte Unicode: setas, box-drawing, acentos).

Dependências (venv /tmp/opencode/pdfenv): reportlab, markdown
Uso:
    /tmp/opencode/pdfenv/bin/python tools/build_pdf.py
"""
import sys
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Preformatted, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "Doc-Tecnica-FarmacoMatch.md"
OUT = ROOT / "assets" / "docs" / "Doc-Tecnica-FarmacoMatch.pdf"

# ----------------- Fontes DejaVu (bom suporte Unicode) -----------------
FONT_REG = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
FONT_ITAL = "DejaVuSans-Oblique"
FONT_MONO = "DejaVuMono"
FONT_MONO_BOLD = "DejaVuMono-Bold"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont(FONT_REG, f"{FONT_DIR}/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFont(TTFont(FONT_ITAL, f"{FONT_DIR}/DejaVuSans-Oblique.ttf"))
        pdfmetrics.registerFont(TTFont(FONT_MONO, f"{FONT_DIR}/DejaVuSansMono.ttf"))
        pdfmetrics.registerFont(TTFont(FONT_MONO_BOLD, f"{FONT_DIR}/DejaVuSansMono-Bold.ttf"))
        pdfmetrics.registerFontFamily(
            FONT_REG, normal=FONT_REG, bold=FONT_BOLD, italic=FONT_ITAL, boldItalic=FONT_BOLD
        )
        return True
    except Exception:
        return False

# fallback Helvetica se DejaVu não estiver disponível
FB_REG, FB_BOLD, FB_MONO = "Helvetica", "Helvetica-Bold", "Courier"

# Paleta (mesma do site/app)
C_TITLE = colors.HexColor("#2C3E50")
C_SUB = colors.HexColor("#7F8C8D")
C_PRIMARY = colors.HexColor("#3498DB")
C_PRIMARY_DARK = colors.HexColor("#2980B9")
C_BORDER = colors.HexColor("#E5E8EC")
C_CODEBG = colors.HexColor("#F4F6F8")
C_TEXT = colors.HexColor("#2C3E50")
C_LABEL = colors.HexColor("#34495E")


def make_styles(use_dejavu):
    reg = FONT_REG if use_dejavu else FB_REG
    bold = FONT_BOLD if use_dejavu else FB_BOLD
    mono = FONT_MONO if use_dejavu else FB_MONO
    mono_bold = FONT_MONO_BOLD if use_dejavu else FB_MONO

    ss = getSampleStyleSheet()
    base = ParagraphStyle(
        "Body", parent=ss["BodyText"], fontName=reg, fontSize=10,
        leading=15, textColor=C_TEXT, alignment=TA_LEFT, spaceAfter=6,
    )
    styles = {
        "h1": ParagraphStyle("h1", parent=base, fontName=bold, fontSize=20,
                              leading=24, textColor=C_TITLE, spaceBefore=2, spaceAfter=8,
                              alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=base, fontName=bold, fontSize=14,
                             leading=18, textColor=C_PRIMARY_DARK, spaceBefore=14, spaceAfter=5),
        "h3": ParagraphStyle("h3", parent=base, fontName=bold, fontSize=11.5,
                             leading=15, textColor=C_TITLE, spaceBefore=10, spaceAfter=3),
        "body": base,
        "quote": ParagraphStyle("quote", parent=base, fontName=reg,
                                 leftIndent=14, textColor=C_SUB, spaceAfter=8),
        "li": ParagraphStyle("li", parent=base, leftIndent=6, spaceAfter=3),
        "code": ParagraphStyle("code", parent=base, fontName=mono, fontSize=8.2, leading=11.5,
                               textColor=C_TEXT, spaceAfter=6,
                               backColor=C_CODEBG, borderPadding=6, leftIndent=4, rightIndent=4),
        "th": ParagraphStyle("th", parent=base, fontName=bold, fontSize=9,
                             leading=12, textColor=colors.white, spaceAfter=0),
        "td": ParagraphStyle("td", parent=base, fontSize=9, leading=12, textColor=C_TEXT, spaceAfter=0),
        "footer": ParagraphStyle("footer", parent=base, fontSize=8, textColor=C_SUB,
                                 alignment=2),
        "_fonts": (reg, bold, mono, mono_bold),
    }
    return styles


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline(el, mono_font) -> str:
    """Converte nó inline (texto + strong/em/code) em markup do reportlab."""
    parts = []
    if el.text:
        parts.append(esc(el.text))
    for child in el:
        tag = child.tag
        inner = inline(child, mono_font)
        if tag == "strong" or tag == "b":
            parts.append(f"<b>{inner}</b>")
        elif tag == "em" or tag == "i":
            parts.append(f"<i>{inner}</i>")
        elif tag == "code":
            parts.append(f'<font name="{mono_font}" color="#1E5A99">{inner}</font>')
        else:
            parts.append(inner)
        if child.tail:
            parts.append(esc(child.tail))
    return "".join(parts)


def build_table(tbl, styles, mono_font):
    rows = []
    head = tbl.find("thead")
    body = tbl.find("tbody")
    if head is not None:
        for tr in head.findall("tr"):
            cells = []
            for c in tr:
                txt = inline(c, mono_font) or "&nbsp;"
                cells.append(Paragraph(txt, styles["th"]))
            rows.append(cells)
    if body is not None:
        for tr in body.findall("tr"):
            cells = []
            for c in tr:
                txt = inline(c, mono_font) or "&nbsp;"
                cells.append(Paragraph(txt, styles["td"]))
            rows.append(cells)

    if not rows:
        return Spacer(1, 2)
    n_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < n_cols:
            r.append(Paragraph("&nbsp;", styles["td"]))

    avail = 16 * cm
    col_w = avail / n_cols
    t = Table(rows, colWidths=[col_w] * n_cols, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]
    t.setStyle(TableStyle(style))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 6)])


def walk(elements, styles):
    reg, bold, mono, mono_bold = styles["_fonts"]
    flow = []
    for el in elements:
        tag = el.tag
        if tag in ("h1", "h2", "h3"):
            level = tag
            text = inline(el, mono)
            flow.append(Paragraph(text or "", styles[level]))
            if level == "h2":
                flow.append(HRFlowable(width="100%", thickness=0.6,
                                       color=C_BORDER, spaceBefore=2, spaceAfter=4))
        elif tag == "p":
            flow.append(Paragraph(inline(el, mono) or "", styles["body"]))
        elif tag == "blockquote":
            inner = "".join(inline(c, mono) for c in el)
            flow.append(Spacer(1, 2))
            flow.append(Paragraph(inner or "", styles["quote"]))
        elif tag == "ul":
            items = []
            for li in el.findall("li"):
                items.append(ListItem(Paragraph(inline(li, mono) or "", styles["li"]),
                                      leftIndent=10, value="•"))
            flow.append(ListFlowable(items, bulletType="bullet", start="•",
                                     leftIndent=10, bulletFontName=reg,
                                     bulletFontSize=9, spaceAfter=4))
        elif tag == "ol":
            items = []
            for i, li in enumerate(el.findall("li"), 1):
                items.append(ListItem(Paragraph(inline(li, mono) or "", styles["li"]),
                                      leftIndent=14, value=str(i)))
            flow.append(ListFlowable(items, bulletType="1", leftIndent=14,
                                     spaceAfter=4))
        elif tag == "pre":
            code_el = el.find("code")
            text = (code_el.text if code_el is not None else el.text) or ""
            text = text.rstrip("\n")
            flow.append(Preformatted(text, styles["code"]))
        elif tag == "table":
            flow.append(build_table(el, styles, mono))
        elif tag == "hr":
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            flow.append(Spacer(1, 4))
        elif tag == "code":
            flow.append(Paragraph(f'<font name="{mono}">{inline(el, mono)}</font>',
                                 styles["body"]))
        else:
            txt = "".join(el.itertext())
            if txt.strip():
                flow.append(Paragraph(esc(txt), styles["body"]))
    return flow


def on_page(canvas, doc, styles):
    reg, bold, mono, _ = styles["_fonts"]
    canvas.saveState()
    canvas.setFont(reg, 8)
    canvas.setFillColor(C_SUB)
    canvas.drawString(2 * cm, 1.2 * cm, "FarmacoMatch — Documentação Técnica")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


def main():
    if not SRC.exists():
        print(f"Documento fonte não encontrado: {SRC}", file=sys.stderr)
        return 1
    use_dejavu = register_fonts()
    md_text = SRC.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"])
    html = md.convert(md_text)
    root = ET.fromstring("<root>" + html + "</root>")

    styles = make_styles(use_dejavu)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title="Documentação Técnica — FarmacoMatch",
        author="FarmacoMatch / Unifil",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame],
                     onPage=lambda c, d: on_page(c, d, styles))
    ])

    flow = walk(list(root), styles)
    doc.build(flow)
    size = OUT.stat().st_size
    print(f"OK -> {OUT} ({size/1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())