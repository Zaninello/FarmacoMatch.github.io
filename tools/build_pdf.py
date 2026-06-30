#!/usr/bin/env python3
"""
Gera o PDF da Documentação Técnica a partir do arquivo .txt (texto puro).

Parseia o formato plain-text:
  - Linha 1            → título (h1)
  - Linhas antes do 1º ===  → subtítulo/metadados
  - === (linha cheia)  → separador de seção (HR)
  - --- (linha cheia)  → delimitador de bloco de código
  - "N. Texto"         → heading nível 2
  - "N.N Texto"        → heading nível 3
  - 4+ espaços indent. → bloco pré-formatado (código/diagrama)
  - "- "               → item de lista

Dependências (venv /tmp/opencode/pdfenv): reportlab
Uso:
    /tmp/opencode/pdfenv/bin/python tools/build_pdf.py
"""
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    HRFlowable, Preformatted, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "Doc-Tecnica-FarmacoMatch.txt"
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

# ----------------- Paleta -----------------
C_TITLE = colors.HexColor("#2C3E50")
C_SUB = colors.HexColor("#7F8C8D")
C_PRIMARY = colors.HexColor("#3498DB")
C_PRIMARY_DARK = colors.HexColor("#2980B9")
C_BORDER = colors.HexColor("#E5E8EC")
C_CODEBG = colors.HexColor("#F4F6F8")
C_TEXT = colors.HexColor("#2C3E50")
C_LABEL = colors.HexColor("#34495E")

# ----------------- Parser -----------------
def is_separator(line, char):
    s = line.strip()
    return len(s) > 10 and set(s) == {char}

def parse_blocks(text):
    lines = text.split("\n")
    n = len(lines)
    blocks = []
    i = 0

    # --- Título + metadados (antes do primeiro ===) ---
    meta_lines = []
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if is_separator(lines[i], "="):
            i += 1
            break
        meta_lines.append(s)
        i += 1

    if meta_lines:
        blocks.append(("h1", meta_lines[0]))
        for m in meta_lines[1:]:
            blocks.append(("meta", m))

    # --- Resto do documento ---
    while i < n:
        raw = lines[i]
        s = raw.strip()

        # linha vazia
        if not s:
            i += 1
            continue

        # separador ===
        if is_separator(raw, "="):
            blocks.append(("hr", None))
            i += 1
            continue

        # bloco de código delimitado por ---
        if is_separator(raw, "-"):
            i += 1
            code_lines = []
            while i < n:
                if is_separator(lines[i], "-"):
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(code_lines).rstrip()))
            continue

        # bloco indentado (4+ espaços) → pré-formatado
        if raw.startswith("    "):
            code_lines = []
            while i < n and (lines[i].startswith("    ") or lines[i].strip() == ""):
                if lines[i].strip() == "" and i + 1 < n and not lines[i + 1].startswith("    "):
                    break
                code_lines.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(code_lines).rstrip()))
            continue

        # heading "N.N Texto"
        if re.match(r"^\d+\.\d+\s", s):
            blocks.append(("h3", re.sub(r"^\d+\.\d+\s*", "", s)))
            i += 1
            continue

        # heading "N. Texto"
        if re.match(r"^\d+\.\s", s):
            blocks.append(("h2", re.sub(r"^\d+\.\s*", "", s)))
            i += 1
            continue

        # lista "- ..."
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            blocks.append(("list", items))
            continue

        # parágrafo
        para_lines = [s]
        i += 1
        while i < n:
            ns = lines[i].strip()
            if (not ns or is_separator(lines[i], "=") or is_separator(lines[i], "-")
                    or ns.startswith("- ") or re.match(r"^\d+\.\s", ns)
                    or re.match(r"^\d+\.\d+\s", ns) or lines[i].startswith("    ")):
                break
            para_lines.append(ns)
            i += 1
        blocks.append(("p", " ".join(para_lines)))

    return blocks


# ----------------- Renderização -----------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def style_inline(text):
    """Converte marcações simples: `codigo`, **negrito**, → ↔ (Unicode direto)."""
    s = esc(text)
    # `codigo`
    s = re.sub(r"`([^`]+)`", r'<font name="%s" color="#1E5A99">\1</font>' % FONT_MONO, s)
    return s


def make_styles(use_dejavu):
    reg = FONT_REG if use_dejavu else FB_REG
    bold = FONT_BOLD if use_dejavu else FB_BOLD
    mono = FONT_MONO if use_dejavu else FB_MONO
    mono_bold = FONT_MONO_BOLD if use_dejavu else FB_MONO

    body = ParagraphStyle(
        "Body", fontName=reg, fontSize=10, leading=15, textColor=C_TEXT,
        alignment=TA_LEFT, spaceAfter=6,
    )
    return {
        "h1": ParagraphStyle("h1", parent=body, fontName=bold, fontSize=20, leading=24,
                             textColor=C_TITLE, spaceBefore=2, spaceAfter=8, alignment=TA_CENTER),
        "meta": ParagraphStyle("meta", parent=body, fontName=reg, fontSize=10, leading=14,
                               textColor=C_SUB, alignment=TA_CENTER, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=body, fontName=bold, fontSize=14, leading=18,
                             textColor=C_PRIMARY_DARK, spaceBefore=14, spaceAfter=5),
        "h3": ParagraphStyle("h3", parent=body, fontName=bold, fontSize=11.5, leading=15,
                             textColor=C_TITLE, spaceBefore=10, spaceAfter=3),
        "body": body,
        "code": ParagraphStyle("code", parent=body, fontName=mono, fontSize=8.2, leading=11.5,
                               textColor=C_TEXT, spaceAfter=6, backColor=C_CODEBG,
                               borderPadding=6, leftIndent=4, rightIndent=4),
        "li": ParagraphStyle("li", parent=body, leftIndent=6, spaceAfter=3),
        "footer": ParagraphStyle("footer", parent=body, fontSize=8, textColor=C_SUB, alignment=2),
        "_fonts": (reg, bold, mono, mono_bold),
    }


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


def build(text, out_path):
    use_dejavu = register_fonts()
    styles = make_styles(use_dejavu)
    blocks = parse_blocks(text)

    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title="Documentação Técnica — FarmacoMatch",
        author="FarmacoMatch / Unifil",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame],
                     onPage=lambda c, d: on_page(c, d, styles))
    ])

    flow = []
    for btype, content in blocks:
        if btype == "h1":
            flow.append(Paragraph(style_inline(content), styles["h1"]))
        elif btype == "meta":
            flow.append(Paragraph(style_inline(content), styles["meta"]))
        elif btype == "h2":
            flow.append(Spacer(1, 4))
            flow.append(Paragraph(style_inline(content), styles["h2"]))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=C_BORDER,
                                   spaceBefore=2, spaceAfter=4))
        elif btype == "h3":
            flow.append(Paragraph(style_inline(content), styles["h3"]))
        elif btype == "p":
            flow.append(Paragraph(style_inline(content), styles["body"]))
        elif btype == "list":
            items = [
                ListItem(Paragraph(style_inline(item), styles["li"]),
                         leftIndent=10, value="•")
                for item in content
            ]
            flow.append(ListFlowable(items, bulletType="bullet", start="•",
                                     leftIndent=10, bulletFontName=styles["_fonts"][0],
                                     bulletFontSize=9, spaceAfter=4))
        elif btype == "code":
            flow.append(Preformatted(content, styles["code"]))
            flow.append(Spacer(1, 2))
        elif btype == "hr":
            flow.append(Spacer(1, 6))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            flow.append(Spacer(1, 6))

    doc.build(flow)


def main():
    if not SRC.exists():
        print(f"Fonte não encontrada: {SRC}", file=sys.stderr)
        return 1
    text = SRC.read_text(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    build(text, OUT)
    size = OUT.stat().st_size
    print(f"OK -> {OUT} ({size/1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())