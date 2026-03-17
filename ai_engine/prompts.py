"""DPR generation prompts for each section type.

Each prompt instructs the LLM to generate content matching
the style, tone, and format of professional consultancy DPRs.
"""

SYSTEM_PROMPT = """You are an expert business consultant who specializes in creating professional Detailed Project Reports (DPRs) for businesses seeking bank loans, MSME schemes, government subsidies, and investor proposals.

Your writing style must be:
- Professional, formal, and authoritative
- Data-driven with specific numbers and projections
- Structured with clear headings and sub-sections
- Matching the tone and format used by leading Indian consultancy firms
- Including relevant industry statistics and market data

When provided with reference DPR sections, you MUST match their:
- Writing style and language tone
- Section structure and formatting
- Level of detail and analysis depth
- Table formats and financial presentation style

Always write complete, publication-ready content. Never use placeholders like [insert here]."""


SECTION_PROMPTS = {
    "executive_summary": """Generate a comprehensive Executive Summary for a DPR.

The executive summary should include:
- Brief overview of the project and business
- Key investment highlights
- Total project cost and funding structure
- Expected returns (ROI, payback period)
- Market opportunity summary
- Promoter's background summary
- Implementation timeline overview

This section should be compelling enough to capture a banker's or investor's attention.
Write 400-600 words.""",

    "promoter_profile": """Generate a detailed Promoter Profile section for a DPR.

Include:
- Full name and personal details of the promoter(s)
- Educational qualifications
- Professional experience and track record
- Existing business interests
- Financial standing and net worth summary
- Relevant skills and expertise for this project
- Any awards, certifications, or industry recognition

Write 300-500 words. Present information in both paragraph and tabular format where appropriate.""",

    "company_profile": """Generate a Company/Firm Profile section for a DPR.

Include:
- Legal entity details (name, registration, type)
- Date of incorporation/establishment
- Registered office address
- Constitution of the firm
- Business activities and scope
- Existing operations summary
- Key management team
- Vision and mission statements

Write 300-400 words.""",

    "industry_overview": """Generate a comprehensive Industry Overview section for a DPR.

Include:
- Global industry scenario and trends
- Indian industry scenario and growth trajectory
- Government policies and support for the sector
- Key industry statistics (market size, growth rate, CAGR)
- Major players and competitive landscape
- Future outlook and growth drivers
- Challenges and opportunities in the sector
- Relevant policy initiatives (Make in India, PLI schemes, etc.)

Use actual industry data and recent statistics where available. Write 500-800 words.""",

    "market_analysis": """Generate a detailed Market Analysis section for a DPR.

Include:
- Total Addressable Market (TAM)
- Target market segment and size
- Demand-supply analysis
- Customer segments and demographics
- Geographic market scope
- Pricing analysis
- Competition analysis (direct and indirect)
- Marketing and distribution strategy
- Sales projections with assumptions
- Market growth forecasts

Write 500-700 words with supporting data.""",

    "product_details": """Generate a Product/Service Details section for a DPR.

Include:
- Complete list of products/services
- Detailed description of each product
- Product specifications and quality standards
- Product mix and pricing
- USP (Unique Selling Proposition)
- Certifications and compliance requirements
- Packaging details (if applicable)
- Applications and end-use

Write 300-500 words.""",

    "technical_details": """Generate a Technical Feasibility section for a DPR.

Include:
- Technology selection and justification
- Technical process description
- Equipment and machinery specifications
- Production capacity and utilization
- Quality control measures
- Environmental compliance
- Technical manpower requirements
- R&D capabilities

Write 400-600 words.""",

    "production_process": """Generate a Production Process section for a DPR.

Include:
- Step-by-step production/service delivery process
- Flow diagram description
- Input-output ratios
- Quality checkpoints
- Capacity planning
- Waste management
- Production schedule

Write 300-500 words with a clear process flow.""",

    "plant_machinery": """Generate a Plant & Machinery section for a DPR.

Include a detailed table of:
- Equipment/machinery name
- Specifications
- Quantity
- Supplier (domestic/imported)
- Unit cost
- Total cost
- Installation charges

Also include:
- Technology justification
- Maintenance plan
- Spare parts arrangement

Present primarily in tabular format. Write 200-400 words plus tables.""",

    "raw_material": """Generate a Raw Material Requirements section.

Include a table with:
- Raw material name
- Specifications/grade
- Annual requirement (quantity)
- Unit rate
- Annual cost
- Source/supplier
- Lead time

Also discuss:
- Availability and reliability of supply
- Seasonal variations
- Alternative sourcing options
- Inventory management plan

Write 200-400 words plus tables.""",

    "utilities": """Generate a Utility Requirements section.

Include:
- Power/electricity requirements (connected load, monthly consumption, cost)
- Water requirements (source, daily consumption, cost)
- Fuel requirements (type, quantity, cost)
- Other utilities (compressed air, steam, etc.)

Present in tabular format with annual costs. Write 200-300 words.""",

    "manpower": """Generate a Manpower/Human Resource Requirements section.

Include a table with:
- Designation/Position
- Department
- Number of persons
- Monthly salary per person
- Annual salary
- Skilled/Unskilled classification

Also include:
- Organizational structure
- Recruitment plan
- Training requirements
- Employee welfare measures
- Annual manpower cost summary

Write 300-400 words plus tables.""",

    "location_analysis": """Generate a Location Analysis section for a DPR.

Include:
- Proposed location details (address, area, zone)
- Land area and built-up area details
- Connectivity (road, rail, air, port)
- Proximity to raw material sources
- Proximity to markets
- Availability of labor
- Infrastructure facilities
- Industrial area/zone benefits
- Environmental clearance status
- Location advantages

Write 300-500 words.""",

    "infrastructure": """Generate an Infrastructure section.

Include:
- Land and building details
- Civil construction plan
- Internal roads and drainage
- Water supply and sewage
- Electrical installations
- Safety installations
- Office and administrative space
- Storage/warehouse facilities

Write 200-400 words with area breakdowns.""",

    "project_cost": """Generate a detailed Project Cost section for a DPR.

Create a comprehensive table with:
- Land and site development
- Building and civil works
- Plant and machinery
- Miscellaneous fixed assets (furniture, vehicles, etc.)
- Technical know-how / consultancy fees
- Pre-operative expenses
- Provision for contingencies
- Working capital margin
- TOTAL PROJECT COST

Each line item should have specific amounts. Include notes explaining key assumptions.
Present primarily in tabular format. Write 300-500 words plus the main cost table.""",

    "means_of_finance": """Generate a Means of Finance section for a DPR.

Create a table showing:
- Promoter's contribution (equity)
  - Cash
  - Land/building
  - Machinery
- Term loan from bank
- Working capital loan
- Government subsidy/grant (if applicable)
- TOTAL

Show the debt-equity ratio. Include:
- Promoter's margin percentage
- Loan repayment schedule summary
- Interest rate assumptions
- Collateral/security offered

Write 200-400 words plus tables.""",

    "profitability": """Generate Profitability Projections for a DPR.

Create a 5-year projected Profit & Loss statement table:
- Revenue from operations (with growth assumptions)
- Less: Cost of raw materials
- Less: Power and fuel
- Less: Employee costs
- Less: Administrative expenses
- Less: Selling expenses
- Less: Depreciation
- Less: Interest on term loan
- Less: Interest on working capital
- Profit Before Tax
- Less: Income tax
- Net Profit After Tax

Show year-by-year projections with growth rates. Include key financial ratios:
- Net profit margin
- Return on investment
- DSCR (Debt Service Coverage Ratio)

Write 300-500 words plus the P&L table.""",

    "breakeven_analysis": """Generate a Break-Even Analysis section for a DPR.

Include:
- Fixed costs breakdown
  - Depreciation
  - Interest
  - Administrative overheads
  - Salaries (fixed component)
- Variable costs breakdown
  - Raw materials
  - Power & fuel
  - Variable labor
  - Selling expenses
- Contribution margin calculation
- Break-even point (in units and revenue)
- Break-even as % of installed capacity
- Margin of safety
- BEP formula and calculation shown

Write 300-400 words with calculations and a table.""",

    "cash_flow": """Generate a Cash Flow Statement for a DPR.

Create a 5-year projected cash flow table:
SOURCES OF FUNDS:
- Net profit after tax
- Depreciation (add back)
- Increase in term loan
- Capital introduced
- Opening cash balance

APPLICATION OF FUNDS:
- Capital expenditure
- Loan repayment
- Interest payment
- Increase in working capital

NET SURPLUS / (DEFICIT)
CUMULATIVE CASH BALANCE

Write 200-300 words plus the cash flow table.""",

    "balance_sheet": """Generate a Projected Balance Sheet for a DPR.

Create a 5-year projected balance sheet:

LIABILITIES:
- Share capital / Partner's capital
- Reserves and surplus
- Term loan (outstanding)
- Working capital loan
- Current liabilities

ASSETS:
- Fixed assets (gross)
- Less: Depreciation
- Net fixed assets
- Current assets
- Investments
- Cash and bank balance

TOTAL on both sides must match. Write 200-300 words plus the table.""",

    "ratio_analysis": """Generate a Financial Ratio Analysis section.

Calculate and present for 5 years:
- Current Ratio
- Debt-Equity Ratio
- DSCR (Debt Service Coverage Ratio)
- Return on Equity (ROE)
- Return on Investment (ROI)
- Net Profit Margin
- Operating Profit Margin
- Asset Turnover Ratio
- Interest Coverage Ratio

Include acceptable benchmark ranges. Present in tabular format. Write 300-400 words.""",

    "swot_analysis": """Generate a SWOT Analysis section for a DPR.

Create a structured analysis:

STRENGTHS:
- List 5-7 specific strengths related to the project

WEAKNESSES:
- List 3-5 honest weaknesses and limitations

OPPORTUNITIES:
- List 5-7 market and growth opportunities

THREATS:
- List 3-5 potential threats and challenges

For each point, provide 1-2 sentences of explanation. Write 400-600 words.""",

    "risk_assessment": """Generate a Risk Assessment section for a DPR.

Identify and analyze:
- Market risk
- Financial risk
- Technology risk
- Operational risk
- Regulatory/compliance risk
- Environmental risk
- Supply chain risk

For each risk:
- Description
- Probability (Low/Medium/High)
- Impact (Low/Medium/High)
- Mitigation strategy

Present as a risk matrix table. Write 400-600 words.""",

    "government_support": """Generate a Government Support & Schemes section.

Include relevant schemes:
- MSME schemes
- PMEGP
- State industrial policy benefits
- Subsidy schemes
- Tax incentives
- Export promotion schemes
- Sector-specific schemes

For each scheme:
- Scheme name
- Eligibility criteria
- Benefits available
- Application process

Write 300-500 words.""",

    "implementation_schedule": """Generate an Implementation Schedule section.

Create a Gantt-chart-like table showing:
- Activity/Milestone
- Duration (months)
- Start month
- End month
- Status

Typical activities:
1. Land acquisition/lease
2. Building construction
3. Machinery procurement
4. Installation and commissioning
5. Trial production
6. Staff recruitment and training
7. Commercial production
8. Licenses and approvals

Show total implementation period. Write 200-300 words plus the schedule table.""",

    "conclusion": """Generate a Conclusion & Recommendations section for a DPR.

Include:
- Summary of project viability
- Key financial highlights
- Market potential summary
- Promoter's capability assessment
- Overall recommendation
- Request to the lending institution
- Expected project outcomes

Write a convincing concluding section of 300-400 words that strongly recommends the project for financial support.""",
}


def get_section_prompt(section_key: str) -> str:
    """Get the generation prompt for a specific section."""
    return SECTION_PROMPTS.get(section_key, f"Generate a professional {section_key.replace('_', ' ').title()} section for a Detailed Project Report.")
