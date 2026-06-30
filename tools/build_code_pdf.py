#!/usr/bin/env python3
"""
Gera o PDF do codigo-fonte (app.py) com visual de IDE:
  - Fundo escuro (#282C34 - tema Atom One Dark)
  - Numeracao de linhas na gutter (coluna esquerda)
  - Syntax highlighting com cores (keyword, string, comment, number, etc.)
  - Fonte monoespacada, espacada, facil de ler

Dependencias (no venv /tmp/opencode/pdfenv): reportlab
Uso:
    /tmp/opencode/pdfenv/bin/python tools/build_code_pdf.py
"""
import sys
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "app.py"
OUT = ROOT / "assets" / "docs" / "Codigo-Fonte-FarmacoMatch.pdf"

# ----------------- Paleta Atom One Dark -----------------
BG          = colors.HexColor("#282C34")
GUTTER_BG   = colors.HexColor("#21252B")
GUTTER_FG   = colors.HexColor("#495162")
TEXT_DEFAULT= colors.HexColor("#ABB2BF")
C_KEYWORD   = colors.HexColor("#C678DD")
C_BUILTIN   = colors.HexColor("#56B6C2")
C_STRING    = colors.HexColor("#98C379")
C_COMMENT   = colors.HexColor("#5C6370")
C_NUMBER    = colors.HexColor("#D19A66")
C_FUNC      = colors.HexColor("#61AFEF")
C_DECORATOR = colors.HexColor("#56B6C2")

CAT_COLOR = {
    "keyword":   C_KEYWORD,
    "builtin":   C_BUILTIN,
    "string":    C_STRING,
    "comment":   C_COMMENT,
    "number":    C_NUMBER,
    "funcdef":   C_FUNC,
    "decorator": C_DECORATOR,
    "default":   TEXT_DEFAULT,
}

# ----------------- Regex tokenizer -----------------
_STR_PREFIX = r'(?:[rRbBuUfF]|[rR][bB]|[bB][rR]|[fF][rR]|[rR][fF])?'

TOKEN_RE = re.compile(
    r'(?P<comment>\#[^\n]*)'
    r'|(?P<triple>' + _STR_PREFIX + r'"""[\s\S]*?"""|' + _STR_PREFIX + r"'''[\s\S]*?''')"
    r'|(?P<string>' + _STR_PREFIX + r'"[^"\n]*"|' + _STR_PREFIX + r"'[^'\n]*')"
    r'|(?P<number>\b\d+\.?\d*(?:[eE][+-]?\d+)?\b)'
    r'|(?P<keyword>\b(?:def|class|if|elif|else|for|while|import|from|as|return|try|except|'
    r'finally|with|pass|break|continue|in|not|and|or|is|None|True|False|lambda|yield|'
    r'raise|assert|del|global|nonlocal|async|await)\b)'
    r'|(?P<builtin>\b(?:print|len|range|str|int|float|list|dict|set|tuple|bool|open|'
    r'isinstance|hasattr|getattr|setattr|type|enumerate|zip|map|filter|sorted|reversed|'
    r'sum|min|max|abs|round|format|input|super|Exception|ValueError|TypeError|KeyError|'
    r'IndexError|AttributeError|self|cls|cursor|conn)\b)'
    r'|(?P<funcdef>[A-Za-z_]\w*(?=\s*\())'
    r'|(?P<decorator>@[A-Za-z_][\w.]*)'
    r'|(?P<name>[A-Za-z_]\w*)'
    r'|(?P<ws>[ \t]+)'
    r'|(?P<newline>\n)'
    r'|(?P<other>.)'
)

CATEGORY_ORDER = [
    "comment", "triple", "string", "number", "keyword", "builtin",
    "funcdef", "decorator", "name", "ws", "newline", "other"
]


def tokenize_to_lines(code: str):
    """Tokeniza o codigo e agrupa por linha. Retorna list de listas de (text, cat)."""
    lines = [[]]  # lines[0] = linha 1
    for m in TOKEN_RE.finditer(code):
        cat = m.lastgroup
        text = m.group()
        if cat == "newline":
            lines.append([])
            continue
        if cat in ("triple", "string"):
            color_cat = "string"
        elif cat == "ws":
            color_cat = "default"
        else:
            color_cat = cat
        # se o token contem newlines (triple-string), quebra em varias linhas
        if "\n" in text:
            parts = text.split("\n")
            for i, part in enumerate(parts):
                if part:
                    lines[-1].append((part, color_cat))
                if i < len(parts) - 1:
                    lines.append([])
        else:
            lines[-1].append((text, color_cat))
    return lines


# ----------------- Fonte monoespacada -----------------
MONO_NAME = "Courier"
MONO_BOLD = "Courier-Bold"


def try_register_mono():
    global MONO_NAME, MONO_BOLD
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "DejaVuMono"),
        ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", "LibMono"),
    ]
    for reg, bold, name in candidates:
        try:
            pdfmetrics.registerFont(TTFont(name, reg))
            try:
                pdfmetrics.registerFont(TTFont(name + "-Bold", bold))
                MONO_BOLD = name + "-Bold"
            except Exception:
                MONO_BOLD = name
            MONO_NAME = name
            return
        except Exception:
            continue


def draw_code_pdf(code: str, out_path: Path):
    try_register_mono()

    tokenized_lines = tokenize_to_lines(code)
    n_lines = len(tokenized_lines)

    PAGE_W, PAGE_H = A4
    MARGIN_L = 1.4 * cm
    MARGIN_R = 1.2 * cm
    MARGIN_T = 1.8 * cm
    MARGIN_B = 1.8 * cm

    GUTTER_W = 1.4 * cm
    LINE_H = 14.0
    FONT_SIZE = 8.5
    CODE_X = MARGIN_L + GUTTER_W + 8
    GUTTER_X = MARGIN_L

    usable_w = PAGE_W - MARGIN_L - MARGIN_R
    usable_h = PAGE_H - MARGIN_T - MARGIN_B
    lines_per_page = int(usable_h // LINE_H)

    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle("Codigo-Fonte-FarmacoMatch")
    c.setAuthor("FarmacoMatch")
    c.setSubject("Codigo-fonte da aplicacao FarmacoMatch (app.py)")

    total_pages = max(1, (n_lines + lines_per_page - 1) // lines_per_page)

    def draw_page_bg():
        c.setFillColor(BG)
        c.rect(MARGIN_L, MARGIN_B, usable_w, usable_h, fill=1, stroke=0)
        c.setFillColor(GUTTER_BG)
        c.rect(MARGIN_L, MARGIN_B, GUTTER_W, usable_h, fill=1, stroke=0)

    def draw_header(page_num):
        c.setFillColor(colors.HexColor("#1B1F27"))
        c.rect(MARGIN_L, PAGE_H - MARGIN_T + 6, usable_w, 16, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#ABB2BF"))
        c.setFont(MONO_NAME, 7.5)
        c.drawString(MARGIN_L + 8, PAGE_H - MARGIN_T + 11, "  app.py")
        c.setFillColor(colors.HexColor("#56B6C2"))
        c.drawRightString(PAGE_W - MARGIN_R - 8, PAGE_H - MARGIN_T + 11,
                          f"Python 3  -  FarmacoMatch  -  pagina {page_num}/{total_pages}")

    def draw_footer(page_num):
        c.setFillColor(colors.HexColor("#5C6370"))
        c.setFont(MONO_NAME, 7)
        c.drawString(MARGIN_L, MARGIN_B - 14,
                     "Codigo-fonte estatico do app.py  -  PDF gerado para leitura")
        c.drawRightString(PAGE_W - MARGIN_R, MARGIN_B - 14, f"{page_num}/{total_pages}")

    page = 1
    y = PAGE_H - MARGIN_T - LINE_H + 8
    first_line_idx = 0

    while first_line_idx < n_lines:
        draw_page_bg()
        draw_header(page)
        last_line_idx = min(first_line_idx + lines_per_page, n_lines)

        for i in range(first_line_idx, last_line_idx):
            line_num = i + 1
            # numero da linha na gutter
            c.setFillColor(GUTTER_FG)
            c.setFont(MONO_NAME, FONT_SIZE)
            c.drawRightString(GUTTER_X + GUTTER_W - 8, y, str(line_num))

            # codigo
            segments = tokenized_lines[i] if i < len(tokenized_lines) else []
            x = CODE_X
            for text, cat in segments:
                color = CAT_COLOR.get(cat, TEXT_DEFAULT)
                font = MONO_BOLD if cat == "keyword" else MONO_NAME
                c.setFillColor(color)
                c.setFont(font, FONT_SIZE)
                # quebra se exceder largura
                tw = pdfmetrics.stringWidth(text, font, FONT_SIZE)
                if x + tw > PAGE_W - MARGIN_R:
                    break
                c.drawString(x, y, text)
                x += tw
            y -= LINE_H

        draw_footer(page)
        c.showPage()
        page += 1
        first_line_idx = last_line_idx
        y = PAGE_H - MARGIN_T - LINE_H + 8

    c.save()


def main():
    if not SRC.exists():
        print(f"Fonte nao encontrada: {SRC}", file=sys.stderr)
        return 1
    code = SRC.read_text(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw_code_pdf(code, OUT)
    size = OUT.stat().st_size
    print(f"OK -> {OUT} ({size/1024:.1f} KiB, {len(code.splitlines())} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())