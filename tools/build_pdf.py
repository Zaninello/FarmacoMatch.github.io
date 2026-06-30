#!/usr/bin/env python3
"""
Converte Doc-Tecnica-FarmacoMatch.md em PDF estilizado.
Dependências: reportlab, markdown  (instaladas no venv /tmp/opencode/pdfenv)

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
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Preformatted, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent.parent          # FarmacoMatch.github.io/
SRC = ROOT / "tools" / "Doc-Tecnica-FarmacoMatch.md"    # cópia local (auto-contida)
OUT = ROOT / "assets" / "docs" / "Doc-Tecnica-FarmacoMatch.pdf"

# ----- Fontes (fallback para fonte padrão se Inter não estiver disponível) -----
BASE_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"
MONO_FONT = "Courier"

# Paleta (mesma do site/app)
C_TITLE = colors.HexColor("#2C3E50")
C_SUB = colors.HexColor("#7F8C8D")
C_PRIMARY = colors.HexColor("#3498DB")
C_PRIMARY_DARK = colors.HexColor("#2980B9")
C_BORDER = colors.HexColor("#E5E8EC")
C_CODEBG = colors.HexColor("#F4F6F8")
C_TEXT = colors.HexColor("#2C3E50")
C_LABEL = colors.HexColor("#34495E")


def make_styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle(
        "Body", parent=ss["BodyText"], fontName=BASE_FONT, fontSize=10,
        leading=15, textColor=C_TEXT, alignment=TA_LEFT, spaceAfter=6,
    )
    styles = {
        "h1": ParagraphStyle("h1", parent=base, fontName=BOLD_FONT, fontSize=22,
                              leading=26, textColor=C_TITLE, spaceBefore=4, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName=BOLD_FONT, fontSize=15,
                              leading=19, textColor=C_PRIMARY_DARK, spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName=BOLD_FONT, fontSize=12,
                              leading=16, textColor=C_TITLE, spaceBefore=10, spaceAfter=4),
        "body": base,
        "quote": ParagraphStyle("quote", parent=base, fontName=BASE_FONT,
                                 leftIndent=14, textColor=C_SUB, spaceAfter=8),
        "li": ParagraphStyle("li", parent=base, leftIndent=6, spaceAfter=3),
        "code": ParagraphStyle("code", parent=base, fontName=MONO_FONT, fontSize=8.3,
                               leading=11, textColor=C_TEXT, spaceAfter=6,
                               backColor=C_CODEBG, borderPadding=6),
        "th": ParagraphStyle("th", parent=base, fontName=BOLD_FONT, fontSize=9,
                             leading=12, textColor=colors.white, spaceAfter=0),
        "td": ParagraphStyle("td", parent=base, fontSize=9, leading=12, textColor=C_TEXT, spaceAfter=0),
        "footer": ParagraphStyle("footer", parent=base, fontSize=8, textColor=C_SUB,
                                 alignment=2),
    }
    return styles


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline(el) -> str:
    """Converte nó inline (texto + strong/em/code) em markup do reportlab."""
    parts = []
    if el.text:
        parts.append(esc(el.text))
    for child in el:
        tag = child.tag
        inner = inline(child)
        if tag == "strong" or tag == "b":
            parts.append(f"<b>{inner}</b>")
        elif tag == "em" or tag == "i":
            parts.append(f"<i>{inner}</i>")
        elif tag == "code":
            parts.append(f'<font name="{MONO_FONT}" color="#1E5A99">{inner}</font>')
        else:
            parts.append(inner)
        if child.tail:
            parts.append(esc(child.tail))
    return "".join(parts)


def build_table(tbl, styles):
    rows = []
    # header
    head = tbl.find("thead")
    body = tbl.find("tbody")
    if head is not None:
        for tr in head.findall("tr"):
            cells = []
            for c in tr:
                txt = inline(c) or "&nbsp;"
                cells.append(Paragraph(txt, styles["th"]))
            rows.append(cells)
    if body is not None:
        for tr in body.findall("tr"):
            cells = []
            for c in tr:
                txt = inline(c) or "&nbsp;"
                cells.append(Paragraph(txt, styles["td"]))
            rows.append(cells)

    if not rows:
        return Spacer(1, 2)
    n_cols = max(len(r) for r in rows)
    # normaliza
    for r in rows:
        while len(r) < n_cols:
            r.append(Paragraph("&nbsp;", styles["td"]))

    avail = 16 * cm  # largura útil
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
    flow = []
    for el in elements:
        tag = el.tag
        if tag in ("h1", "h2", "h3"):
            level = tag
            text = inline(el)
            flow.append(Paragraph(text or "", styles[level]))
            if level == "h2":
                flow.append(HRFlowable(width="100%", thickness=0.6,
                                       color=C_BORDER, spaceBefore=2, spaceAfter=4))
        elif tag == "p":
            flow.append(Paragraph(inline(el) or "", styles["body"]))
        elif tag == "blockquote":
            inner = "".join(inline(c) for c in el)
            flow.append(Spacer(1, 2))
            flow.append(Paragraph(inner or "", styles["quote"]))
        elif tag == "ul":
            items = []
            for li in el.findall("li"):
                items.append(ListItem(Paragraph(inline(li) or "", styles["li"]),
                                      leftIndent=10, value="•"))
            flow.append(ListFlowable(items, bulletType="bullet", start="•",
                                     leftIndent=10, bulletFontName=BASE_FONT,
                                     bulletFontSize=9, spaceAfter=4))
        elif tag == "ol":
            items = []
            for i, li in enumerate(el.findall("li"), 1):
                items.append(ListItem(Paragraph(inline(li) or "", styles["li"]),
                                      leftIndent=14, value=str(i)))
            flow.append(ListFlowable(items, bulletType="1", leftIndent=14,
                                     spaceAfter=4))
        elif tag == "pre":
            code_el = el.find("code")
            text = (code_el.text if code_el is not None else el.text) or ""
            text = text.rstrip("\n")
            flow.append(Preformatted(text, styles["code"]))
        elif tag == "table":
            flow.append(build_table(el, styles))
        elif tag == "hr":
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            flow.append(Spacer(1, 4))
        elif tag == "code":
            # code solto fora de pre — trata como parágrafo monospace
            flow.append(Paragraph(f'<font name="{MONO_FONT}">{inline(el)}</font>',
                                 styles["body"]))
        else:
            # desconhecido: tenta renderizar texto
            txt = "".join(el.itertext())
            if txt.strip():
                flow.append(Paragraph(esc(txt), styles["body"]))
    return flow


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(BASE_FONT, 8)
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
    md_text = SRC.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"])
    html = md.convert(md_text)
    root = ET.fromstring("<root>" + html + "</root>")

    styles = make_styles()
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
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=on_page)])

    flow = walk(list(root), styles)
    doc.build(flow)
    size = OUT.stat().st_size
    print(f"OK -> {OUT} ({size/1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())