"""Main DPR generator: orchestrates section-by-section generation."""
import asyncio
from typing import Tuple
from ai_engine.rag_pipeline import generate_section_with_rag
from ai_engine.llm_client import generate_text
from ai_engine.prompts import SYSTEM_PROMPT
from document_parser.section_extractor import get_section_order, SECTION_DISPLAY_NAMES
from financial.models import generate_financial_data


# Default sections to generate
DEFAULT_SECTIONS = [
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
    "project_cost",
    "means_of_finance",
    "profitability",
    "breakeven_analysis",
    "cash_flow",
    "swot_analysis",
    "risk_assessment",
    "implementation_schedule",
    "conclusion",
]


async def generate_full_dpr(
    inputs: dict,
    document_texts: list[str] | None = None,
    custom_instructions: str | None = None,
    sections_to_generate: list[str] | None = None,
) -> Tuple[dict, dict]:
    """
    Generate a complete DPR with all sections.
    
    Returns:
        Tuple of (sections_dict, financial_data_dict)
    """
    sections = sections_to_generate or DEFAULT_SECTIONS

    # If we have document texts, add them to inputs context
    if document_texts:
        combined_text = "\n\n".join(document_texts[:5])  # Limit to first 5 docs
        if len(combined_text) > 10000:
            combined_text = combined_text[:10000]
        inputs["_uploaded_document_context"] = combined_text

    if custom_instructions:
        inputs["_custom_instructions"] = custom_instructions

    # Generate financial data first (used by financial sections)
    financial_data = generate_financial_data(inputs)
    inputs["_financial_data"] = financial_data

    # Generate sections (with some parallelism, batched to avoid rate limits)
    generated_sections = {}
    batch_size = 3

    for i in range(0, len(sections), batch_size):
        batch = sections[i:i + batch_size]
        tasks = [generate_section_with_rag(section_key, inputs) for section_key in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for section_key, result in zip(batch, results):
            if isinstance(result, Exception):
                print(f"Error generating {section_key}: {result}")
                generated_sections[section_key] = f"[Error generating this section: {str(result)}]"
            else:
                generated_sections[section_key] = result

    return generated_sections, financial_data


async def regenerate_section(
    section_key: str,
    inputs: dict,
    existing_sections: dict,
    instructions: str | None = None,
) -> str:
    """Regenerate a specific section with optional custom instructions."""
    if instructions:
        inputs["_custom_instructions"] = instructions

    content = await generate_section_with_rag(section_key, inputs)
    return content
