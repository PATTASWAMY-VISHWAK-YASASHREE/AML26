"""Create a polished PDF from the research Markdown report.

This intentionally uses a small, deterministic ReportLab renderer rather than
shell markdown converters, so the final artifact can be inspected locally.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_URL_RE = re.compile(r'https?://[^\s<>"]+')
_TRAILING_PUNCT = ".,;:!?"


def esc(text: str) -> str:
    """Escape every character ReportLab's markup parser treats as significant."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _link_markup(match: re.Match[str]) -> str:
    url = match.group(0)
    trail = ""
    while url and url[-1] in _TRAILING_PUNCT:
        trail = url[-1] + trail
        url = url[:-1]
    while url.endswith(")") and url.count(")") > url.count("("):
        trail = ")" + trail
        url = url[:-1]
    if not url:
        return match.group(0)
    href = url.replace('"', "&quot;").replace("'", "&#39;")
    return f'<link href="{href}" color="#1f5a99">{url}</link>{trail}'


def inline(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    text = _URL_RE.sub(_link_markup, text)
    return text


def split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", text)]


def make_pdf(md: Path, out: Path) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.5, spaceAfter=5, textColor=colors.HexColor("#202124")))
    styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27, alignment=TA_CENTER, textColor=colors.HexColor("#16324f"), spaceAfter=16))
    styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#16324f"), spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="H3X", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor("#1f5a99"), spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.0, leading=10, textColor=colors.HexColor("#3f4b5b")))

    styles.add(ParagraphStyle(name="CodeX", parent=styles["BodyText"], fontName="Courier", fontSize=8.4, leading=10.6, textColor=colors.HexColor("#1b2733")))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d9e2ec"))
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(18 * mm, 8 * mm, "Amazon ML Challenge 2026 | Research and proxy validation")
        canvas.drawRightString(192 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def build_code_block(code_lines):
        """Render a fenced block literally: no inline markdown inside command examples."""
        data = [[Paragraph(esc(x) if x else "&nbsp;", styles["CodeX"])] for x in code_lines]
        tbl = Table(data, colWidths=[174 * mm])
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6f9")), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        return [tbl, Spacer(1, 6)]

    def build_table(rows):
        """Render a markdown table, padding short rows to the widest row."""
        ncols = max(len(row) for row in rows)
        rows = [list(row) + [""] * (ncols - len(row)) for row in rows]
        data = [[Paragraph(inline(x), styles["SmallX"]) for x in row] for row in rows]
        widths = [174 * mm / ncols] * ncols
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return [tbl, Spacer(1, 8)]

    story = []
    in_code = False
    code_lines = []
    table_rows = []
    for raw in md.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            # A table may still be buffered; flush it first so the emitted order
            # matches the markdown source.
            if table_rows:
                story += build_table(table_rows)
                table_rows = []
            if in_code:
                story += build_code_block(code_lines)
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|") and "|" in line[1:]:
            cells = split_table_row(line)
            if all(set(x) <= set("-: ") for x in cells):
                continue
            table_rows.append(cells)
            continue
        if table_rows:
            story += build_table(table_rows)
            table_rows = []
        if not line:
            story.append(Spacer(1, 3))
        elif line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["TitleX"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["H2X"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["H3X"]))
        elif line.startswith("---"):
            story.append(Spacer(1, 4))
        elif line.startswith("- "):
            story.append(Paragraph("• " + inline(line[2:]), styles["BodyX"]))
        else:
            story.append(Paragraph(inline(line), styles["BodyX"]))
    if in_code:
        raise ValueError(f"unterminated fenced code block in {md}")
    if table_rows:
        story += build_table(table_rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title="Amazon ML Challenge 2026 Research Report", author="Hermes Agent")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    make_pdf(root / "reports/research_report.md", root / "reports/Amazon_ML_Challenge_2026_Research_Report.pdf")
