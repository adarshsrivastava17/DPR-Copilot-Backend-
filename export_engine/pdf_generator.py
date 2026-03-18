"""Professional PDF report generator – single dark-olive color theme with elegant cover page."""
import os
import re
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from config import get_settings

settings = get_settings()

# ─── Single Color Palette (Dark Olive) ─────────────────
PRIMARY      = HexColor("#3C4A3E")   # Dark olive – main brand color
PRIMARY_DARK = HexColor("#2B342C")   # Deeper olive for cover bg
PRIMARY_MID  = HexColor("#4E5E50")   # Mid tone for accents
ACCENT       = HexColor("#B8C5A3")   # Muted sage – accent/highlight
ACCENT_WARM  = HexColor("#C4B99A")   # Warm tan for "Prepared by" box
TEXT_LIGHT   = HexColor("#E8E6E1")   # Off-white text on dark bg
TEXT_DARK    = HexColor("#2A2A2A")   # Near-black for body text
GRAY         = HexColor("#777777")   # Secondary text
LIGHT_BG     = HexColor("#F5F4F0")   # Very light olive tint for alt rows
TABLE_BORDER = HexColor("#D5D3CE")   # Subtle table borders
WHITE        = HexColor("#FFFFFF")

SECTION_NAMES = {
    "executive_summary": "Executive Summary",
    "promoter_profile": "Promoter & Company Profile",
    "industry_overview": "Industry & Market Analysis",
    "product_details": "Product / Service Details",
    "technical_details": "Technical Feasibility & Production",
    "project_cost": "Project Cost & Means of Finance",
    "profitability": "Profitability & Financial Projections",
    "swot_analysis": "SWOT Analysis",
    "risk_assessment": "Risk Assessment & Mitigation",
    "conclusion": "Conclusion & Recommendations",
}


# ━━━━━━━━━━━━━━━━━━ Custom Flowables ━━━━━━━━━━━━━━━━━━

class CoverPage(Flowable):
    """Full-page dark cover with dot pattern, project name, year, and info box."""
    def __init__(self, project_name, business_type=""):
        Flowable.__init__(self)
        self.project_name = project_name
        self.business_type = business_type

    def wrap(self, availWidth, availHeight):
        # Return small size – actual drawing happens full-page via coords
        return (availWidth, availHeight - 40)

    def draw(self):
        c = self.canv
        w, h = A4

        # ── Full dark background ──
        c.setFillColor(PRIMARY_DARK)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # ── Dot/halftone pattern in top-right area ──
        c.setFillColor(PRIMARY_MID)
        # Create a halftone-style dot pattern that fades from right-top
        for row in range(35):
            for col in range(25):
                x = w - 30 - col * 12
                y = h - 50 - row * 12
                if x < w * 0.3 or y < h * 0.35:
                    continue
                # Dots get smaller as they go left and down (fade effect)
                dist_factor = (col / 25) + (row / 35)
                if dist_factor > 1.2:
                    continue
                dot_size = max(0.5, 3.5 - dist_factor * 3)
                # Add randomness via position-based offset
                offset = ((row * 7 + col * 13) % 5) * 0.3
                c.circle(x + offset, y + offset, dot_size, fill=1, stroke=0)

        # ── Year box (top-right) ──
        year = str(datetime.now().year)
        c.setFillColor(TEXT_LIGHT)
        c.setFont("Helvetica", 16)
        c.drawRightString(w - 50, h - 65, year)

        # ── "DETAILED PROJECT REPORT" small label ──
        c.setFillColor(ACCENT)
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 260, "DETAILED PROJECT REPORT")

        # ── Thin accent line ──
        c.setStrokeColor(ACCENT)
        c.setLineWidth(0.8)
        c.line(50, h - 268, 250, h - 268)

        # ── Project name (large, bold) ──
        c.setFillColor(TEXT_LIGHT)
        c.setFont("Helvetica-Bold", 36)

        # Word-wrap the project name into lines of ~18 chars
        words = self.project_name.upper().split()
        lines = []
        current = ""
        for word in words:
            if current and len(current + " " + word) > 18:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            lines.append(current)

        y_start = h - 320
        for i, line_text in enumerate(lines):
            c.drawString(50, y_start - i * 50, line_text)

        # ── Business type (smaller, below name) ──
        if self.business_type:
            y_type = y_start - len(lines) * 50 - 10
            c.setFillColor(ACCENT)
            c.setFont("Helvetica", 13)
            c.drawString(50, y_type, self.business_type.title())

        # ── "Prepared by" info box at bottom ──
        box_w = w - 100
        box_h = 55
        box_x = 50
        box_y = 55

        c.setFillColor(ACCENT_WARM)
        c.roundRect(box_x, box_y, box_w, box_h, 4, fill=1, stroke=0)

        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 9)
        c.drawString(box_x + 15, box_y + 35, "Prepared by")
        c.setFont("Helvetica-Bold", 13)
        c.drawString(box_x + 15, box_y + 14, self.project_name)

        # Date on right side of box
        c.setFont("Helvetica", 9)
        c.drawString(box_x + box_w - 160, box_y + 35, "Date")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(box_x + box_w - 160, box_y + 14, datetime.now().strftime("%d %B %Y"))


class ColoredBar(Flowable):
    """Simple colored horizontal bar."""
    def __init__(self, width, height, color, radius=0):
        Flowable.__init__(self)
        self.bar_width = width
        self.bar_height = height
        self.color = color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.color)
        if self.radius:
            self.canv.roundRect(0, 0, self.bar_width, self.bar_height, self.radius, fill=1, stroke=0)
        else:
            self.canv.rect(0, 0, self.bar_width, self.bar_height, fill=1, stroke=0)

    def wrap(self, availWidth, availHeight):
        return (self.bar_width, self.bar_height)


class SectionHeader(Flowable):
    """Elegant section header with number badge – single color."""
    def __init__(self, section_num, section_name):
        Flowable.__init__(self)
        self.section_num = section_num
        self.section_name = section_name

    def draw(self):
        c = self.canv
        w = 450

        # Light background
        c.setFillColor(LIGHT_BG)
        c.roundRect(0, -5, w, 45, 6, fill=1, stroke=0)

        # Left accent bar
        c.setFillColor(PRIMARY)
        c.roundRect(0, -5, 6, 45, 3, fill=1, stroke=0)

        # Number badge
        c.setFillColor(PRIMARY)
        c.roundRect(16, 3, 30, 30, 6, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(31, 12, str(self.section_num).zfill(2))

        # Title
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(56, 14, self.section_name)

    def wrap(self, availWidth, availHeight):
        return (450, 48)


# ━━━━━━━━━━━━━━━━━━ Main Generator ━━━━━━━━━━━━━━━━━━

def generate_pdf(
    report_id: str,
    title: str,
    sections: dict,
    financial_data: dict,
    project_name: str,
    business_type: str = "",
) -> str:
    """Generate an elegant single-color PDF report."""
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    pdf_path = os.path.join(settings.REPORTS_DIR, f"{report_id}.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=50, rightMargin=50,
        topMargin=65, bottomMargin=60,
    )

    styles = _create_styles()
    story = []

    # ─── Cover Page (drawn via onFirstPage callback) ─
    # We store cover info for the callback, then add a spacer + page break
    doc._cover_project_name = project_name
    doc._cover_business_type = business_type
    story.append(PageBreak())

    # ─── Table of Contents ───────────────────────────
    story.append(SectionHeader(0, "TABLE OF CONTENTS"))
    story.append(Spacer(1, 20))

    for i, key in enumerate(sections.keys(), 1):
        display_name = SECTION_NAMES.get(key, key.replace("_", " ").title())
        toc_data = [[
            Paragraph(f"<b>{i}</b>", styles["toc_num"]),
            Paragraph(display_name, styles["toc_name"]),
            Paragraph(f"Section {i}", styles["toc_page"]),
        ]]
        toc_table = Table(toc_data, colWidths=[35, 330, 80])
        toc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (0, 0), WHITE),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (1, 0), (-1, 0), LIGHT_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, TABLE_BORDER),
        ]))
        story.append(toc_table)
        story.append(Spacer(1, 3))

    story.append(PageBreak())

    # ─── Sections ────────────────────────────────────
    for i, (key, content) in enumerate(sections.items(), 1):
        display_name = SECTION_NAMES.get(key, key.replace("_", " ").title())

        story.append(SectionHeader(i, display_name))
        story.append(Spacer(1, 15))

        _parse_markdown_content(content or "", story, styles)

        # Financial tables
        if key == "project_cost" and financial_data.get("project_cost"):
            story.append(Spacer(1, 10))
            story.append(_build_themed_table(financial_data["project_cost"], "Project Cost", styles))

        if key in ("means_of_finance", "project_cost") and financial_data.get("means_of_finance"):
            story.append(Spacer(1, 10))
            story.append(_build_mof_table(financial_data["means_of_finance"], styles))

        if key == "profitability" and financial_data.get("revenue_projections"):
            story.append(Spacer(1, 10))
            story.append(_build_pl_table(financial_data["revenue_projections"], styles))

        if key == "breakeven_analysis" and financial_data.get("breakeven"):
            story.append(Spacer(1, 10))
            story.append(_build_bep_table(financial_data["breakeven"], styles))

        # Section end accent line
        story.append(Spacer(1, 15))
        story.append(ColoredBar(450, 2, PRIMARY))
        story.append(PageBreak())

    doc.build(story, onFirstPage=_draw_cover_page, onLaterPages=_add_header_footer)
    return pdf_path


# ━━━━━━━━━━━━━━━━━━ Content Parser ━━━━━━━━━━━━━━━━━━

def _parse_markdown_content(content: str, story: list, styles: dict):
    """Parse markdown into styled ReportLab flowables – single color."""
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            story.append(Spacer(1, 4))
            i += 1
            continue

        # ── Table ──
        if line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            el = _markdown_table_to_reportlab(table_lines, styles)
            if el:
                story.append(Spacer(1, 6))
                story.append(el)
                story.append(Spacer(1, 6))
            continue

        # ── Headings ──
        if line.startswith("#### "):
            text = _clean_md(line[5:])
            story.append(Spacer(1, 6))
            h = Table([[Paragraph(text, styles["heading4"])]], colWidths=[440])
            h.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 1, PRIMARY),
            ]))
            story.append(h)
            i += 1
            continue

        if line.startswith("### "):
            text = _clean_md(line[4:])
            story.append(Spacer(1, 8))
            h = Table(
                [[ColoredBar(4, 18, PRIMARY), Paragraph(text, ParagraphStyle(
                    "DynH3", fontName="Helvetica-Bold", fontSize=11, textColor=PRIMARY, leading=14))]],
                colWidths=[10, 430]
            )
            h.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(h)
            i += 1
            continue

        if line.startswith("## "):
            text = _clean_md(line[3:])
            story.append(Spacer(1, 10))
            h = Table(
                [[ColoredBar(6, 22, PRIMARY), Paragraph(text, ParagraphStyle(
                    "DynH2", fontName="Helvetica-Bold", fontSize=13, textColor=PRIMARY, leading=16))]],
                colWidths=[12, 428]
            )
            h.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("BACKGROUND", (1, 0), (1, 0), LIGHT_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(h)
            i += 1
            continue

        if line.startswith("# "):
            text = _clean_md(line[2:])
            story.append(Spacer(1, 10))
            story.append(Paragraph(text, styles["heading2"]))
            i += 1
            continue

        # ── Horizontal rule ──
        if line.strip() in ("---", "***", "___"):
            story.append(Spacer(1, 4))
            story.append(ColoredBar(440, 1, TABLE_BORDER))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # ── Bullet ──
        if line.strip().startswith(("- ", "• ", "* ")):
            text = line.strip()
            for pfx in ["- ", "• ", "* "]:
                if text.startswith(pfx):
                    text = text[len(pfx):]
                    break
            text = _clean_md(text)
            bt = Table(
                [[ColoredBar(5, 5, PRIMARY), Paragraph(text, styles["body"])]],
                colWidths=[15, 425]
            )
            bt.setStyle(TableStyle([
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(bt)
            i += 1
            continue

        # ── Emoji bullets ──
        if any(line.strip().startswith(e) for e in ["✅ ", "⚠️ ", "🚀 ", "⚡ "]):
            text = _clean_md(line.strip())
            story.append(Paragraph(f"    {text}", styles["body"]))
            i += 1
            continue

        # ── Numbered list ──
        num_match = re.match(r"^(\d+)\.\s+(.+)", line.strip())
        if num_match:
            num = num_match.group(1)
            text = _clean_md(num_match.group(2))
            nt = Table(
                [[Paragraph(f"<b>{num}</b>", ParagraphStyle("Num", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
                  Paragraph(text, styles["body"])]],
                colWidths=[22, 418]
            )
            nt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), PRIMARY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (0, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
            ]))
            story.append(nt)
            story.append(Spacer(1, 2))
            i += 1
            continue

        # ── Regular paragraph ──
        text = _clean_md(line.strip())
        if text:
            story.append(Paragraph(text, styles["body"]))
        i += 1


# ━━━━━━━━━━━━━━━━━━ Table Builders ━━━━━━━━━━━━━━━━━━

def _markdown_table_to_reportlab(table_lines: list, styles: dict):
    """Convert markdown table to styled ReportLab table."""
    if len(table_lines) < 2:
        return None

    header_cells = [c.strip() for c in table_lines[0].split("|") if c.strip()]
    data_rows = []
    for line in table_lines[1:]:
        if re.match(r"^\|[\s\-:]+\|", line):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if cells:
            data_rows.append(cells)

    if not header_cells:
        return None

    num_cols = len(header_cells)
    hdr_style = ParagraphStyle("THdr", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, alignment=TA_LEFT)
    cell_style = ParagraphStyle("TCell", fontName="Helvetica", fontSize=9, textColor=TEXT_DARK)

    all_rows = [[Paragraph(_clean_md(c), hdr_style) for c in header_cells]]
    for row in data_rows:
        while len(row) < num_cols:
            row.append("")
        row = row[:num_cols]
        all_rows.append([Paragraph(_clean_md(c), cell_style) for c in row])

    col_w = 450 / num_cols
    table = Table(all_rows, colWidths=[col_w] * num_cols)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 2, PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


# ━━━━━━━━━━━━━━━━━━ Helpers ━━━━━━━━━━━━━━━━━━━━━━━━━

def _clean_md(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<i>\1</i>", text)
    text = text.lstrip("#").strip()
    text = text.replace("&", "&amp;")
    text = text.replace("<b>", "BOLD_OPEN").replace("</b>", "BOLD_CLOSE")
    text = text.replace("<i>", "ITAL_OPEN").replace("</i>", "ITAL_CLOSE")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("BOLD_OPEN", "<b>").replace("BOLD_CLOSE", "</b>")
    text = text.replace("ITAL_OPEN", "<i>").replace("ITAL_CLOSE", "</i>")
    return text


def _create_styles():
    base = getSampleStyleSheet()
    s = {}
    s["cover_title"]  = ParagraphStyle("CT", parent=base["Title"], fontSize=28, textColor=PRIMARY, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s["cover_subtitle"] = ParagraphStyle("CS", parent=base["Title"], fontSize=20, textColor=PRIMARY_MID, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s["cover_type"]   = ParagraphStyle("CType", parent=base["Normal"], fontSize=14, textColor=GRAY, alignment=TA_CENTER)
    s["heading2"]     = ParagraphStyle("H2", parent=base["Heading2"], fontSize=13, textColor=PRIMARY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6)
    s["heading3"]     = ParagraphStyle("H3", parent=base["Heading3"], fontSize=11, textColor=PRIMARY_MID, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    s["heading4"]     = ParagraphStyle("H4", parent=base["Normal"], fontSize=10, textColor=PRIMARY, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=3)
    s["body"]         = ParagraphStyle("Body", parent=base["Normal"], fontSize=10, textColor=TEXT_DARK, leading=14, alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=4)
    s["bullet"]       = ParagraphStyle("Bullet", parent=base["Normal"], fontSize=10, textColor=TEXT_DARK, leading=14, leftIndent=20, spaceBefore=2, spaceAfter=2)
    s["toc_num"]      = ParagraphStyle("TN", parent=base["Normal"], fontSize=10, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s["toc_name"]     = ParagraphStyle("TNm", parent=base["Normal"], fontSize=11, textColor=TEXT_DARK, fontName="Helvetica", leftIndent=8)
    s["toc_page"]     = ParagraphStyle("TP", parent=base["Normal"], fontSize=9, textColor=GRAY, alignment=TA_RIGHT)
    s["table_header"] = ParagraphStyle("TH", parent=base["Normal"], fontSize=9, textColor=WHITE, fontName="Helvetica-Bold")
    s["table_cell"]   = ParagraphStyle("TC", parent=base["Normal"], fontSize=9, textColor=TEXT_DARK)
    return s


def _draw_cover_page(canvas, doc):
    """Draw the full-bleed dark cover page directly on canvas."""
    canvas.saveState()
    c = canvas
    w, h = A4
    project_name = getattr(doc, '_cover_project_name', 'Project Report')
    business_type = getattr(doc, '_cover_business_type', '')

    # Full dark background
    c.setFillColor(PRIMARY_DARK)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Dot/halftone pattern in top-right
    c.setFillColor(PRIMARY_MID)
    for row in range(35):
        for col in range(25):
            x = w - 30 - col * 12
            y = h - 50 - row * 12
            if x < w * 0.3 or y < h * 0.35:
                continue
            dist_factor = (col / 25) + (row / 35)
            if dist_factor > 1.2:
                continue
            dot_size = max(0.5, 3.5 - dist_factor * 3)
            offset = ((row * 7 + col * 13) % 5) * 0.3
            c.circle(x + offset, y + offset, dot_size, fill=1, stroke=0)

    # Year (top-right)
    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica", 16)
    c.drawRightString(w - 50, h - 65, str(datetime.now().year))

    # "DETAILED PROJECT REPORT" label
    c.setFillColor(ACCENT)
    c.setFont("Helvetica", 10)
    c.drawString(50, h - 260, "DETAILED PROJECT REPORT")
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    c.line(50, h - 268, 250, h - 268)

    # Project name (large, bold)
    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica-Bold", 36)
    words = project_name.upper().split()
    lines = []
    current = ""
    for word in words:
        if current and len(current + " " + word) > 18:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    y_start = h - 320
    for i, line_text in enumerate(lines):
        c.drawString(50, y_start - i * 50, line_text)

    # Business type
    if business_type:
        y_type = y_start - len(lines) * 50 - 10
        c.setFillColor(ACCENT)
        c.setFont("Helvetica", 13)
        c.drawString(50, y_type, business_type.title())

    # "Prepared by" info box at bottom
    box_w = w - 100
    box_h = 55
    box_x = 50
    box_y = 55
    c.setFillColor(ACCENT_WARM)
    c.roundRect(box_x, box_y, box_w, box_h, 4, fill=1, stroke=0)
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 9)
    c.drawString(box_x + 15, box_y + 35, "Prepared by")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(box_x + 15, box_y + 14, project_name)
    c.setFont("Helvetica", 9)
    c.drawString(box_x + box_w - 160, box_y + 35, "Date")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(box_x + box_w - 160, box_y + 14, datetime.now().strftime("%d %B %Y"))

    canvas.restoreState()


def _add_header_footer(canvas, doc):
    """Elegant single-color header and footer for content pages."""
    canvas.saveState()
    w, h = A4

    # Header bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, h - 25, w, 25, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 27, w, 2, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(WHITE)
    canvas.drawString(50, h - 18, "DETAILED PROJECT REPORT")
    canvas.drawRightString(w - 50, h - 18, "CONFIDENTIAL")

    # Footer bar
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, 0, w, 22, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 22, w, 2, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(WHITE)
    canvas.drawString(50, 7, f"{doc.project_name} — Detailed Project Report" if hasattr(doc, 'project_name') else "Detailed Project Report")
    canvas.drawRightString(w - 50, 7, f"Page {doc.page}")

    canvas.restoreState()


def _format_inr(amount):
    if amount >= 10000000:
        return f"Rs. {amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"Rs. {amount/100000:.2f} L"
    else:
        return f"Rs. {amount:,.0f}"


def _build_themed_table(data: dict, title: str, styles):
    header = [Paragraph("Particulars", styles["table_header"]), Paragraph("Amount (Rs.)", styles["table_header"])]
    rows = [header]
    for name, key in [("Land & Site", "land_and_site"), ("Building & Civil", "building_civil"),
                      ("Plant & Machinery", "plant_machinery"), ("Misc. Fixed Assets", "misc_fixed_assets"),
                      ("Pre-operative Exp.", "preoperative_expenses"), ("Contingency", "contingency"),
                      ("Working Capital", "working_capital_margin")]:
        rows.append([name, _format_inr(data.get(key, 0))])
    rows.append([Paragraph("<b>TOTAL</b>", styles["table_header"]),
                 Paragraph(f"<b>{_format_inr(data.get('total', 0))}</b>", styles["table_header"])])
    table = Table(rows, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY), ("BACKGROUND", (0, -1), (-1, -1), PRIMARY),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _build_mof_table(data, styles):
    header = [Paragraph("Source", styles["table_header"]), Paragraph("Amount (Rs.)", styles["table_header"])]
    rows = [header]
    for name, key in [("Promoter's Contribution", "promoter_contribution"), ("Term Loan", "term_loan"),
                      ("Working Capital Loan", "working_capital_loan"), ("Subsidy / Grant", "subsidy")]:
        rows.append([name, _format_inr(data.get(key, 0))])
    rows.append([Paragraph("<b>TOTAL</b>", styles["table_header"]),
                 Paragraph(f"<b>{_format_inr(data.get('total', 0))}</b>", styles["table_header"])])
    table = Table(rows, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY), ("BACKGROUND", (0, -1), (-1, -1), PRIMARY),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _build_pl_table(projections, styles):
    header = [Paragraph("Particulars", styles["table_header"])]
    for yr in projections:
        header.append(Paragraph(f"Year {yr['year']}", styles["table_header"]))
    rows = [header]
    for label, key in [("Revenue", "revenue"), ("Raw Material", "raw_material"), ("Salaries", "salaries"),
                       ("Admin Exp.", "admin_expenses"), ("Depreciation", "depreciation"),
                       ("Interest", "interest_term_loan"), ("PBT", "profit_before_tax"),
                       ("Tax", "tax"), ("Net Profit", "net_profit")]:
        row = [label]
        for yr in projections:
            row.append(_format_inr(yr.get(key, 0)))
        rows.append(row)
    cw = 85
    table = Table(rows, colWidths=[130] + [cw] * len(projections))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
    ]))
    return table


def _build_bep_table(data, styles):
    rows = [
        [Paragraph("Particulars", styles["table_header"]), Paragraph("Amount", styles["table_header"])],
        ["Fixed Costs", _format_inr(data.get("fixed_costs", 0))],
        ["Variable Costs", _format_inr(data.get("variable_costs", 0))],
        ["Total Revenue", _format_inr(data.get("total_revenue", 0))],
        ["BEP Revenue", _format_inr(data.get("bep_revenue", 0))],
        ["BEP % Capacity", f"{data.get('bep_percentage', 0)}%"],
    ]
    table = Table(rows, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table
