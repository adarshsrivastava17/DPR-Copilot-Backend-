"""RAG pipeline: retrieves relevant DPR sections from ChromaDB and augments LLM generation."""
from vector_store.chroma_store import search, get_collection_count
from vector_store.embeddings import get_embeddings
from ai_engine.llm_client import generate_text_with_context, generate_text
from ai_engine.prompts import SYSTEM_PROMPT, get_section_prompt


async def generate_section_with_rag(
    section_key: str,
    inputs: dict,
    n_references: int = 3,
) -> str:
    """
    Generate a DPR section using RAG:
    1. Retrieve similar sections from reference DPRs
    2. Augment the generation prompt with reference context
    3. Generate the section content
    """
    section_prompt = get_section_prompt(section_key)

    # Build the input context
    input_context = _format_inputs(inputs)

    # Retrieve reference sections from vector store
    reference_context = ""
    if get_collection_count() > 0:
        try:
            # Search for similar sections
            results = search(
                query_text=f"{section_key.replace('_', ' ')} for {inputs.get('business_type', 'business')}",
                n_results=n_references,
                where={"section_type": section_key} if section_key != "full_document" else None,
            )

            if results and results.get("documents") and results["documents"][0]:
                ref_docs = results["documents"][0]
                reference_context = "\n\n---\n\n".join(ref_docs[:n_references])
        except Exception as e:
            print(f"RAG retrieval error for {section_key}: {e}")

    # Build the user prompt
    user_prompt = f"""{section_prompt}

PROJECT DETAILS:
{input_context}

Generate this section now. Match the style and format of the reference documents provided."""

    # Generate with or without RAG context
    if reference_context:
        content = await generate_text_with_context(
            system_prompt=SYSTEM_PROMPT,
            context=f"REFERENCE DPR SECTIONS (match this style):\n\n{reference_context}",
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4000,
        )
    else:
        content = await generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4000,
        )

    return content


def _format_inputs(inputs: dict) -> str:
    """Format project inputs into a readable context string."""
    if not inputs:
        return "No specific project details provided."

    lines = []
    field_labels = {
        "business_name": "Business Name",
        "business_type": "Type of Business",
        "promoter_name": "Promoter Name",
        "promoter_qualification": "Qualification",
        "promoter_experience": "Experience",
        "location": "Project Location",
        "state": "State",
        "district": "District",
        "products": "Products/Services",
        "total_project_cost": "Total Project Cost",
        "term_loan": "Term Loan Required",
        "promoter_contribution": "Promoter's Contribution",
        "land_area": "Land Area",
        "building_area": "Building Area",
        "annual_revenue": "Expected Annual Revenue",
        "num_employees": "Number of Employees",
        "raw_materials": "Key Raw Materials",
        "target_market": "Target Market",
        "capacity": "Production Capacity",
        "machinery_cost": "Machinery Cost",
        "working_capital": "Working Capital",
    }

    for key, label in field_labels.items():
        if key in inputs and inputs[key]:
            lines.append(f"• {label}: {inputs[key]}")

    # Include any additional fields
    for key, value in inputs.items():
        if key not in field_labels and value:
            lines.append(f"• {key.replace('_', ' ').title()}: {value}")

    return "\n".join(lines) if lines else "No specific project details provided."
