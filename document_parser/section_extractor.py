"""Section extractor: identifies and segments DPR sections from parsed text."""
import re
from typing import Dict, List

# Common DPR section headings (case-insensitive patterns)
SECTION_PATTERNS = [
    (r"executive\s+summary", "executive_summary"),
    (r"promoter\s+(?:profile|details|background)", "promoter_profile"),
    (r"(?:company|firm|business)\s+(?:profile|overview|introduction)", "company_profile"),
    (r"industry\s+(?:overview|analysis|scenario)", "industry_overview"),
    (r"market\s+(?:analysis|study|overview|potential|demand)", "market_analysis"),
    (r"technical\s+(?:details|analysis|aspects|feasibility)", "technical_details"),
    (r"product\s+(?:details|description|mix|range)", "product_details"),
    (r"production\s+(?:process|capacity|details)", "production_process"),
    (r"(?:plant|factory|unit)\s*(?:&|and)?\s*(?:machinery|equipment)", "plant_machinery"),
    (r"location\s+(?:analysis|details|advantage)", "location_analysis"),
    (r"(?:project\s+cost|cost\s+of\s+project|total\s+project\s+cost)", "project_cost"),
    (r"means\s+of\s+finance", "means_of_finance"),
    (r"(?:profitability|profit\s*(?:&|and)\s*loss)\s+(?:projections?|statement|estimate)", "profitability"),
    (r"break[\s-]*even\s+(?:analysis|point)", "breakeven_analysis"),
    (r"(?:cash\s+flow|fund\s+flow)", "cash_flow"),
    (r"balance\s+sheet", "balance_sheet"),
    (r"(?:ratio|financial)\s+analysis", "ratio_analysis"),
    (r"swot\s+analysis", "swot_analysis"),
    (r"risk\s+(?:analysis|assessment|mitigation)", "risk_assessment"),
    (r"implementation\s+(?:schedule|plan|timeline)", "implementation_schedule"),
    (r"(?:manpower|human\s+resource|employment)", "manpower"),
    (r"infrastructure", "infrastructure"),
    (r"raw\s+material", "raw_material"),
    (r"utility\s+(?:requirement|details)", "utilities"),
    (r"government\s+(?:support|schemes?|subsid)", "government_support"),
    (r"conclusion|recommendation", "conclusion"),
]


def extract_sections(text: str) -> Dict[str, str]:
    """
    Extract named sections from DPR text.
    Returns a dict mapping section_key -> section_content.
    """
    lines = text.split("\n")
    sections: Dict[str, str] = {}
    current_section = "preamble"
    current_content: List[str] = []

    for line in lines:
        stripped = line.strip()
        matched_section = _match_section(stripped)

        if matched_section:
            # Save previous section
            if current_content:
                content = "\n".join(current_content).strip()
                if content:
                    sections[current_section] = content
            current_section = matched_section
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        content = "\n".join(current_content).strip()
        if content:
            sections[current_section] = content

    return sections


def _match_section(line: str) -> str | None:
    """Check if a line matches a known section heading."""
    if not line or len(line) > 200:
        return None

    # Check if line looks like a heading (short, possibly uppercase or numbered)
    clean = re.sub(r"^\d+[\.\)]\s*", "", line)  # Remove leading numbers
    clean = re.sub(r"^[IVXLCDM]+[\.\)]\s*", "", clean)  # Remove Roman numerals
    clean = clean.strip(":- ")

    for pattern, key in SECTION_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return key

    return None


def get_section_order() -> List[str]:
    """Return the standard section ordering for DPR generation."""
    return [
        "executive_summary",
        "promoter_profile",
        "company_profile",
        "industry_overview",
        "market_analysis",
        "product_details",
        "technical_details",
        "production_process",
        "plant_machinery",
        "raw_material",
        "utilities",
        "manpower",
        "location_analysis",
        "infrastructure",
        "project_cost",
        "means_of_finance",
        "profitability",
        "breakeven_analysis",
        "cash_flow",
        "balance_sheet",
        "ratio_analysis",
        "swot_analysis",
        "risk_assessment",
        "government_support",
        "implementation_schedule",
        "conclusion",
    ]


SECTION_DISPLAY_NAMES = {
    "executive_summary": "Executive Summary",
    "promoter_profile": "Promoter Profile",
    "company_profile": "Company / Firm Profile",
    "industry_overview": "Industry Overview",
    "market_analysis": "Market Analysis",
    "product_details": "Product Details",
    "technical_details": "Technical Feasibility",
    "production_process": "Production Process",
    "plant_machinery": "Plant & Machinery",
    "raw_material": "Raw Material Requirements",
    "utilities": "Utility Requirements",
    "manpower": "Manpower Requirements",
    "location_analysis": "Location Analysis",
    "infrastructure": "Infrastructure",
    "project_cost": "Project Cost",
    "means_of_finance": "Means of Finance",
    "profitability": "Profitability Projections",
    "breakeven_analysis": "Break-Even Analysis",
    "cash_flow": "Cash Flow Statement",
    "balance_sheet": "Projected Balance Sheet",
    "ratio_analysis": "Ratio Analysis",
    "swot_analysis": "SWOT Analysis",
    "risk_assessment": "Risk Assessment",
    "government_support": "Government Support & Schemes",
    "implementation_schedule": "Implementation Schedule",
    "conclusion": "Conclusion & Recommendations",
}
