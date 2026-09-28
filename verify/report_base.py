"""Shared reportlab scaffolding for the ER research-vs-upstream report."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)

OUT = "ER_research_vs_upstream_report.pdf"
W = 176 * mm  # usable text width

INK = colors.HexColor("#12151a")
MUTED = colors.HexColor("#5b6472")
ACCENT = colors.HexColor("#1f4e79")
WARN = colors.HexColor("#9c2b1b")
OKC = colors.HexColor("#1d6b45")
RULE = colors.HexColor("#d7dce3")
BAND = colors.HexColor("#f2f5f8")
CRIT = colors.HexColor("#fdecea")
HIGH = colors.HexColor("#fdf3e3")
MED = colors.HexColor("#eef4fb")

_ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=_ss["Title"], fontName="Helvetica-Bold",
                            fontSize=20, leading=24, textColor=INK, alignment=TA_LEFT, spaceAfter=3),
    "sub": ParagraphStyle("s", parent=_ss["Normal"], fontName="Helvetica",
                          fontSize=10, leading=13.5, textColor=MUTED, spaceAfter=2),
    "h1": ParagraphStyle("h1", parent=_ss["Heading1"], fontName="Helvetica-Bold",
                         fontSize=13.5, leading=17, textColor=ACCENT, spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Helvetica-Bold",
                         fontSize=10.8, leading=13.5, textColor=INK, spaceBefore=10, spaceAfter=3),
    "body": ParagraphStyle("b", parent=_ss["Normal"], fontName="Helvetica", fontSize=9.2,
                           leading=12.8, textColor=INK, spaceAfter=5),
    "bullet": ParagraphStyle("bu", parent=_ss["Normal"], fontName="Helvetica", fontSize=9.2,
                             leading=12.8, textColor=INK, leftIndent=11, bulletIndent=2, spaceAfter=3.2),
    "cap": ParagraphStyle("c", parent=_ss["Normal"], fontName="Helvetica-Oblique",
                          fontSize=8, leading=10.4, textColor=MUTED, spaceBefore=2, spaceAfter=9),
    "mono": ParagraphStyle("m", parent=_ss["Normal"], fontName="Courier", fontSize=7.8,
                           leading=10, textColor=INK),
    "th": ParagraphStyle("th", parent=_ss["Normal"], fontName="Helvetica-Bold", fontSize=8.1,
                         leading=10, textColor=colors.white),
    "td": ParagraphStyle("td", parent=_ss["Normal"], fontName="Helvetica", fontSize=8.1,
                         leading=10.3, textColor=INK),
    "tdm": ParagraphStyle("tdm", parent=_ss["Normal"], fontName="Courier", fontSize=7.4, leading=9.5),
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(t, st="body"):
    return Paragraph(t, S[st])


def bullets(items):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{i}", S["bullet"]) for i in items]


def code(lines):
    if isinstance(lines, (list, tuple)):
        lines = "\n".join(lines)
    return Preformatted(lines, S["mono"])

def tbl(header, rows, widths, mono_cols=(), zebra=True, hdr_bg=ACCENT):
    data = [[Paragraph(esc(h), S["th"]) for h in header]]
    for r in rows:
        data.append([Paragraph(c, S["tdm"] if i in mono_cols else S["td"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [("BACKGROUND", (0, 0), (-1, 0), hdr_bg),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("GRID", (0, 0), (-1, -1), 0.4, RULE),
             ("TOPPADDING", (0, 0), (-1, -1), 4),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 5),
             ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), BAND))
    t.setStyle(TableStyle(style))
    return t


def callout(title, body, bg, border):
    inner = [[Paragraph(f"<b>{title}</b>", S["body"])], [Paragraph(body, S["body"])]]
    t = Table(inner, colWidths=[W], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("BOX", (0, 0), (-1, -1), 0.9, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, 0), 7),
                           ("BOTTOMPADDING", (0, -1), (-1, -1), 8)]))
    return KeepTogether([t, Spacer(1, 8)])


def finding(tag, tagcolor, bg, title, rows):
    tagp = ParagraphStyle("ft", parent=S["body"], fontName="Helvetica-Bold", fontSize=8.4,
                          textColor=colors.white, alignment=TA_LEFT, spaceAfter=0)
    chip = Table([[Paragraph(f"<b>{tag}</b>", tagp)]], colWidths=[20 * mm], hAlign="LEFT")
    chip.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), tagcolor),
                              ("LEFTPADDING", (0, 0), (-1, -1), 6),
                              ("TOPPADDING", (0, 0), (-1, -1), 2),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    data = [[Paragraph(k, S["td"]), Paragraph(v, S["body"])] for k, v in rows]
    t = Table(data, colWidths=[28 * mm, W - 28 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.35, RULE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                           ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("BACKGROUND", (0, 0), (0, -1), bg),
                           ("BACKGROUND", (1, 0), (1, -1), colors.white)]))
    return [chip, Paragraph(title, S["h2"]), Spacer(1, 2), t, Spacer(1, 11)]


def _page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(17 * mm, h - 14 * mm, w - 17 * mm, h - 14 * mm)
    canvas.line(17 * mm, 13 * mm, w - 17 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.1)
    canvas.setFillColor(MUTED)
    canvas.drawString(17 * mm, h - 11.4 * mm,
                      "Amazon ML Challenge 2026 - Entity Resolution - research vs. upstream comparison")
    canvas.drawRightString(w - 17 * mm, 8.6 * mm, f"Page {doc.page}")
    canvas.restoreState()


def make_doc():
    doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                          topMargin=19 * mm, bottomMargin=17 * mm,
                          title="ER Research vs Upstream Comparison", author="Automated review")
    frame = Frame(17 * mm, 17 * mm, A4[0] - 34 * mm, A4[1] - 36 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_page)])
    return doc
