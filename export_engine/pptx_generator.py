"""PowerPoint pitch deck generator using python-pptx."""
import os
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from config import get_settings
from document_parser.section_extractor import SECTION_DISPLAY_NAMES

settings = get_settings()

# Colors
NAVY = RGBColor(0, 51, 102)
TEAL = RGBColor(0, 102, 153)
GOLD = RGBColor(204, 153, 0)
WHITE = RGBColor(255, 255, 255)
DARK = RGBColor(33, 33, 33)
LIGHT_BG = RGBColor(245, 247, 250)


def generate_pptx(
    report_id: str,
    title: str,
    sections: dict,
    financial_data: dict,
    project_name: str,
) -> str:
    """Generate a consulting pitch deck and return the file path."""
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    pptx_path = os.path.join(settings.REPORTS_DIR, f"{report_id}.pptx")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ─── Title Slide ──────────────────────────────────
    _add_title_slide(prs, project_name, title)

    # ─── Table of Contents ────────────────────────────
    _add_toc_slide(prs, sections)

    # ─── Section Slides ──────────────────────────────
    for key, content in sections.items():
        display_name = SECTION_DISPLAY_NAMES.get(key, key.replace("_", " ").title())
        _add_content_slide(prs, display_name, content)

    # ─── Financial Highlights ─────────────────────────
    if financial_data:
        _add_financials_slide(prs, financial_data)

    # ─── Thank You Slide ─────────────────────────────
    _add_closing_slide(prs, project_name)

    prs.save(pptx_path)
    return pptx_path


def _add_title_slide(prs, project_name, subtitle):
    """Add a branded title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    # Background
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = NAVY

    # Gold accent bar
    shape = slide.shapes.add_shape(1, Inches(0), Inches(3.2), Inches(13.333), Inches(0.05))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GOLD
    shape.line.fill.background()

    # Title
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(11), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "DETAILED PROJECT REPORT"
    p.font.size = Pt(40)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    # Subtitle
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(3.5), Inches(11), Inches(1))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = project_name.upper()
    p2.font.size = Pt(28)
    p2.font.color.rgb = GOLD
    p2.font.bold = True
    p2.alignment = PP_ALIGN.CENTER

    # Date
    txBox3 = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11), Inches(0.5))
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = f"Prepared: {datetime.now().strftime('%B %Y')} | Confidential"
    p3.font.size = Pt(14)
    p3.font.color.rgb = WHITE
    p3.alignment = PP_ALIGN.CENTER


def _add_toc_slide(prs, sections):
    """Add table of contents slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Header
    _add_slide_header(slide, "TABLE OF CONTENTS")

    # Content
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(5.5), Inches(5))
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, key in enumerate(list(sections.keys())[:13], 1):
        display = SECTION_DISPLAY_NAMES.get(key, key.replace("_", " ").title())
        p = tf.add_paragraph() if i > 1 else tf.paragraphs[0]
        p.text = f"{i}.  {display}"
        p.font.size = Pt(14)
        p.font.color.rgb = DARK
        p.space_after = Pt(4)

    # Second column if more than 13 sections
    remaining = list(sections.keys())[13:]
    if remaining:
        txBox2 = slide.shapes.add_textbox(Inches(7), Inches(1.5), Inches(5.5), Inches(5))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        for i, key in enumerate(remaining, 14):
            display = SECTION_DISPLAY_NAMES.get(key, key.replace("_", " ").title())
            p = tf2.add_paragraph() if i > 14 else tf2.paragraphs[0]
            p.text = f"{i}.  {display}"
            p.font.size = Pt(14)
            p.font.color.rgb = DARK
            p.space_after = Pt(4)


def _add_content_slide(prs, title, content):
    """Add a content slide with title and bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Header
    _add_slide_header(slide, title)

    # Content area
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.5))
    tf = txBox.text_frame
    tf.word_wrap = True

    # Parse content into bullet points (take first ~800 chars for slide)
    content = content or ""
    lines = content.split("\n")
    char_count = 0
    max_chars = 800

    for line in lines:
        line = line.strip().replace("**", "").replace("*", "").replace("#", "")
        if not line:
            continue

        char_count += len(line)
        if char_count > max_chars:
            break

        is_bullet = line.startswith("- ") or line.startswith("• ") or line.startswith("· ")
        text = line.lstrip("-•· ").strip()

        if not text:
            continue

        if tf.paragraphs[0].text == "":
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        p.text = f"{'•  ' if is_bullet else ''}{text}"
        p.font.size = Pt(12)
        p.font.color.rgb = DARK
        p.space_after = Pt(4)


def _add_financials_slide(prs, financial_data):
    """Add a financial highlights summary slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_slide_header(slide, "FINANCIAL HIGHLIGHTS")

    pc = financial_data.get("project_cost", {})
    mof = financial_data.get("means_of_finance", {})
    bep = financial_data.get("breakeven", {})
    projections = financial_data.get("revenue_projections", [])

    highlights = [
        ("Total Project Cost", _format_inr(pc.get("total", 0))),
        ("Promoter's Contribution", _format_inr(mof.get("promoter_contribution", 0))),
        ("Term Loan", _format_inr(mof.get("term_loan", 0))),
        ("Debt-Equity Ratio", f"{mof.get('debt_equity_ratio', 0)}:1"),
        ("Break-Even Point", f"{bep.get('bep_percentage', 0)}% of capacity"),
    ]

    if projections:
        yr1 = projections[0]
        yr5 = projections[-1]
        highlights.append(("Year 1 Revenue", _format_inr(yr1.get("revenue", 0))))
        highlights.append(("Year 1 Net Profit", _format_inr(yr1.get("net_profit", 0))))
        highlights.append(("Year 5 Revenue", _format_inr(yr5.get("revenue", 0))))

    # Create 2x4 grid of highlight boxes
    for i, (label, value) in enumerate(highlights[:8]):
        col = i % 4
        row = i // 4
        x = Inches(0.8 + col * 3.1)
        y = Inches(1.8 + row * 2.5)

        # Box background
        shape = slide.shapes.add_shape(1, x, y, Inches(2.8), Inches(2))
        shape.fill.solid()
        shape.fill.fore_color.rgb = LIGHT_BG
        shape.line.color.rgb = TEAL
        shape.line.width = Pt(1)

        # Value
        txBox = slide.shapes.add_textbox(x + Inches(0.15), y + Inches(0.3), Inches(2.5), Inches(0.8))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = value
        p.font.size = Pt(20)
        p.font.color.rgb = NAVY
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

        # Label
        txBox2 = slide.shapes.add_textbox(x + Inches(0.15), y + Inches(1.2), Inches(2.5), Inches(0.6))
        tf2 = txBox2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = label
        p2.font.size = Pt(11)
        p2.font.color.rgb = DARK
        p2.alignment = PP_ALIGN.CENTER


def _add_closing_slide(prs, project_name):
    """Add a closing/thank you slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = NAVY

    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(1.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "THANK YOU"
    p.font.size = Pt(44)
    p.font.color.rgb = GOLD
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(11), Inches(1))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = f"{project_name}"
    p2.font.size = Pt(18)
    p2.font.color.rgb = WHITE
    p2.alignment = PP_ALIGN.CENTER

    txBox3 = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11), Inches(0.5))
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = f"Prepared by {project_name}"
    p3.font.size = Pt(12)
    p3.font.color.rgb = WHITE
    p3.alignment = PP_ALIGN.CENTER


def _add_slide_header(slide, title):
    """Add a branded header to a slide."""
    # Gold bar
    shape = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()

    # Title text
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11), Inches(0.7))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(24)
    p.font.color.rgb = WHITE
    p.font.bold = True

    # Gold accent line under header
    line = slide.shapes.add_shape(1, Inches(0), Inches(1.2), Inches(13.333), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = GOLD
    line.line.fill.background()


def _format_inr(amount):
    """Format number in Indian currency notation."""
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return str(amount)

    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.0f}"
