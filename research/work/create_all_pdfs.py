"""Create polished PDFs for the research report and contract addendum."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# A URL run: everything up to whitespace or a markup delimiter.  Sentence
# punctuation and unbalanced closing brackets are stripped back out afterwards.
_URL_RE = re.compile(r'https?://[^\s<>"]+')
_TRAILING_PUNCT = ".,;:!?"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _link_markup(match: re.Match[str]) -> str:
    """Render a captured URL as a ReportLab link, keeping trailing punctuation outside."""
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
    text = text.replace("\\t", "    ")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    text = _URL_RE.sub(_link_markup, text)
    return text


def split_table_row(line: str) -> list[str]:
    """Split a markdown table row into cells.

    Exactly one leading and one trailing pipe are treated as row delimiters, so an
    intentionally empty first/last cell (``|| b |``) keeps its column.  ``\\|``
    escapes are honoured instead of splitting on them.
    """
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", text)]


def build(md_path: Path, pdf_path: Path, title: str) -> None:
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"error: cannot read report markdown: {md_path} ({exc})") from exc
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4, leading=12.8, spaceAfter=5, textColor=colors.HexColor("#202124"))
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#16324f"), spaceAfter=15)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#16324f"), spaceBefore=12, spaceAfter=7)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor("#1f5a99"), spaceBefore=8, spaceAfter=4)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor=colors.HexColor("#3f4b5b"))
    # Paragraph-level colour beats the TableStyle TEXTCOLOR command, so the header
    # row needs its own style or it renders dark-on-dark.
    small_head = ParagraphStyle("SmallHead", parent=small, fontName="Helvetica-Bold", textColor=colors.white)
    code = ParagraphStyle("Code", parent=styles["BodyText"], fontName="Courier", fontSize=9.0, leading=12, leftIndent=7, rightIndent=7, borderPadding=6, backColor=colors.HexColor("#f3f6f9"), borderColor=colors.HexColor("#d9e2ec"), borderWidth=.4, spaceAfter=8)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=3)

    def footer(canvas, doc):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#d9e2ec")); canvas.line(18*mm, 13*mm, 192*mm, 13*mm); canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.HexColor("#667085")); canvas.drawString(18*mm, 8*mm, title); canvas.drawRightString(192*mm, 8*mm, f"Page {doc.page}"); canvas.restoreState()

    story=[]; in_code=False; code_lines=[]; table=[]
    def flush_table():
        nonlocal table
        if not table: return
        ncols=max(len(row) for row in table)
        table=[list(row)+[""]*(ncols-len(row)) for row in table]
        data=[[Paragraph(inline(cell), small_head if r==0 else small) for cell in row] for r,row in enumerate(table)]
        t=Table(data, colWidths=[174*mm/ncols]*ncols, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#16324f")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#cbd5e1")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5)]))
        story.extend([t, Spacer(1,8)]); table=[]

    for raw in lines:
        line=raw.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Paragraph("<br/>".join(esc(x) or "&nbsp;" for x in code_lines), code)); code_lines=[]
            in_code=not in_code
            # A table may still be buffered; emit it before the code block so the
            # document order matches the markdown source.
            flush_table()
            continue
        if in_code: code_lines.append(line); continue
        if line.startswith("|") and "|" in line[1:]:
            cells=split_table_row(line)
            if all(set(x)<=set("-: ") for x in cells): continue
            table.append(cells); continue
        flush_table()
        if not line: story.append(Spacer(1,3))
        elif line.startswith("# "): story.append(Paragraph(inline(line[2:]), title_style))
        elif line.startswith("## "): story.append(Paragraph(inline(line[3:]), h2))
        elif line.startswith("### "): story.append(Paragraph(inline(line[4:]), h3))
        elif line.startswith("- "): story.append(Paragraph("• "+inline(line[2:]), bullet))
        elif re.match(r"^\d+\. ", line): story.append(Paragraph(inline(line), body))
        elif line.startswith("Source: "): story.append(Paragraph("<i>" + inline(line) + "</i>", small))
        else: story.append(Paragraph(inline(line), body))
    if in_code and code_lines: story.append(Paragraph("<br/>".join(esc(x) or "&nbsp;" for x in code_lines), code))
    flush_table()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # Build into a temp file in the same directory and rename on success, so a
    # failure part-way through never leaves a truncated PDF at the final path.
    fd, tmp_name = tempfile.mkstemp(suffix=".pdf", dir=str(pdf_path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        doc=SimpleDocTemplate(str(tmp_path), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=18*mm, title=title, author="Hermes Agent")
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    os.replace(tmp_path, pdf_path)


if __name__ == "__main__":
    root=Path(__file__).resolve().parents[1]
    build(root/"reports/research_report_v2.md", root/"reports/Amazon_ML_Challenge_2026_Research_Report_v2.pdf", "Amazon ML Challenge 2026 | Research Report v2")
    build(root/"reports/contract_addendum.md", root/"reports/Amazon_ML_Challenge_2026_Contract_Addendum.pdf", "Amazon ML Challenge 2026 | Contract Addendum")
