"""Reports API router: generate DPR, list reports, get report, regenerate section, export."""
import threading
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from models.project import Project
from models.report import GeneratedReport
from auth.dependencies import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/reports", tags=["reports"])
settings = get_settings()

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
    "contact_details": "Contact Details",
    "conclusion": "Conclusion & Recommendations",
}

FAST_SECTIONS = list(SECTION_NAMES.keys())


def _format_inr(amount) -> str:
    """Format number as Indian Rupees: ₹7,00,000 style."""
    from financial.models import _parse_amount as parse_amt
    if isinstance(amount, str):
        amount = parse_amt(amount)
    amount = round(float(amount))
    if amount < 0:
        return f"-₹{_format_inr_abs(abs(amount))}"
    return f"₹{_format_inr_abs(amount)}"


def _format_inr_abs(n: int) -> str:
    """Format positive integer in Indian grouping: 12,34,567"""
    s = str(int(n))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    # Group rest in pairs from right
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ','.join(groups) + ',' + last3


class GenerateRequest(BaseModel):
    project_id: str
    custom_instructions: Optional[str] = None
    target_pages: Optional[int] = 30
    selected_sections: Optional[list] = None  # e.g. ["executive_summary", "project_cost", ...]


class SectionUpdateRequest(BaseModel):
    section_key: str
    content: str


class RegenerateSectionRequest(BaseModel):
    section_key: str
    instructions: Optional[str] = None


@router.post("/generate")
async def generate_dpr(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == req.project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    report = GeneratedReport(
        title=f"DPR - {project.name}",
        project_id=project.id,
        status="generating",
    )
    db.add(report)
    project.status = "processing"
    await db.flush()

    report_id = str(report.id)
    project_id = str(project.id)
    project_inputs = dict(project.inputs) if project.inputs else {}
    project_name = project.name

    thread = threading.Thread(
        target=_generate_dpr_sync,
        args=(report_id, project_id, project_inputs, project_name, req.custom_instructions, req.target_pages or 30, req.selected_sections),
        daemon=True,
    )
    thread.start()

    return {
        "report_id": report_id,
        "status": "generating",
        "message": "DPR generation started.",
    }


def _try_openai(client, prompt: str, system: str) -> str | None:
    """Attempt OpenAI call, return None on quota/auth errors."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "insufficient" in err or "billing" in err or "429" in err or "401" in err:
            return None  # Signal to use template
        raise


def _generate_template(section_key: str, inputs: dict, project_name: str, target_pages: int = 30) -> str:
    """Generate professional DPR content using templates. Scales content based on target_pages."""
    from financial.models import _parse_amount

    # Pages per section: target_pages minus 3 (cover+TOC) divided among sections
    pages_per_section = max((target_pages - 3) / 11, 0.7)

    name = inputs.get("business_name", project_name) or project_name
    btype = inputs.get("business_type", "manufacturing") or "manufacturing"
    promoter = inputs.get("promoter_name", "the promoter") or "the promoter"
    location = inputs.get("location", "the proposed location") or "the proposed location"
    state = inputs.get("state", "")
    products = inputs.get("products", "the proposed products/services") or "the proposed products/services"
    employees = inputs.get("num_employees", "25") or "25"
    capacity = inputs.get("capacity", "as per market demand") or "as per market demand"
    loc_full = f"{location}, {state}" if state else location
    raw_materials = inputs.get("raw_materials", "various raw materials as required") or "various raw materials as required"
    target_market = inputs.get("target_market", "domestic and regional markets") or "domestic and regional markets"
    land_area = inputs.get("land_area", "5,000 sq. ft.") or "5,000 sq. ft."
    building_area = inputs.get("building_area", "3,000 sq. ft.") or "3,000 sq. ft."
    qualification = inputs.get("promoter_qualification", "Graduate with relevant professional qualifications") or "Graduate with relevant professional qualifications"
    experience = inputs.get("promoter_experience", "Significant experience in the relevant industry") or "Significant experience in the relevant industry"
    district = inputs.get("district", "")

    # Contact details
    contact_phone = inputs.get("contact_phone", "") or ""
    contact_email = inputs.get("contact_email", "") or ""
    contact_address = inputs.get("contact_address", "") or loc_full
    contact_website = inputs.get("contact_website", "") or ""
    contact_gst = inputs.get("contact_gst", "") or ""
    contact_pan = inputs.get("contact_pan", "") or ""

    # ─── Parse ALL financial values to numbers ─────────
    tpc_num = _parse_amount(inputs.get("total_project_cost", 0))
    if tpc_num <= 0:
        tpc_num = 5000000

    tl_num = _parse_amount(inputs.get("term_loan", 0))
    pc_num = _parse_amount(inputs.get("promoter_contribution", 0))
    mc_num = _parse_amount(inputs.get("machinery_cost", 0))
    wc_num = _parse_amount(inputs.get("working_capital", 0))
    ar_num = _parse_amount(inputs.get("annual_revenue", 0))

    # Calculate missing values
    if tl_num <= 0 and pc_num <= 0:
        tl_num = round(tpc_num * 0.75)
        pc_num = tpc_num - tl_num
    elif tl_num > 0 and pc_num <= 0:
        pc_num = tpc_num - tl_num
    elif pc_num > 0 and tl_num <= 0:
        tl_num = tpc_num - pc_num

    if mc_num <= 0:
        mc_num = round(tpc_num * 0.40)
    if wc_num <= 0:
        wc_num = round(tpc_num * 0.15)
    if ar_num <= 0:
        ar_num = round(tpc_num * 1.5)

    # Calculate project cost breakdown proportionally from total
    wc_margin = round(wc_num * 0.25)
    remaining = tpc_num - mc_num - wc_margin
    remaining = max(remaining, 0)

    land_cost = round(remaining * 0.30)
    building_cost = round(remaining * 0.40)
    misc_assets = round(remaining * 0.12)
    preop_cost = round(remaining * 0.10)
    contingency = tpc_num - mc_num - wc_margin - land_cost - building_cost - misc_assets - preop_cost
    contingency = max(contingency, 0)

    # ─── Format ALL amounts as Indian Rupees ──────────
    total_cost = _format_inr(tpc_num)
    term_loan = _format_inr(tl_num)
    contribution = _format_inr(pc_num)
    machinery_cost = _format_inr(mc_num)
    working_capital = _format_inr(wc_num)
    revenue = _format_inr(ar_num)
    land_cost_f = _format_inr(land_cost)
    building_cost_f = _format_inr(building_cost)
    misc_assets_f = _format_inr(misc_assets)
    preop_cost_f = _format_inr(preop_cost)
    contingency_f = _format_inr(contingency)
    wc_margin_f = _format_inr(wc_margin)
    wc_loan_f = _format_inr(round(wc_num * 0.75))

    # Contribution percentages
    pc_pct = round(pc_num / max(tpc_num, 1) * 100)
    tl_pct = 100 - pc_pct

    # ══════════════════════════════════════════════════
    # Build each section with base + extended tiers
    # Tier 1 added at 1.5+ pages/section (~20+ page report)
    # Tier 2 added at 2.5+ pages/section (~28+ page report)
    # Tier 3 added at 4+ pages/section (~43+ page report)
    # Tier 4 added at 6+ pages/section (~63+ page report)
    # ══════════════════════════════════════════════════

    sections_content = {}

    # ─── EXECUTIVE SUMMARY ──────────────────────────
    base = f"""## Executive Summary

### Project Overview
This Detailed Project Report (DPR) has been prepared for **{name}**, a proposed {btype} venture to be established at {loc_full}. The project envisions the production/provision of {products} to cater to the growing demand in both domestic and regional markets.

The project represents a significant business opportunity in the {btype} sector, backed by favorable market conditions, government support for MSMEs, and the promoter's domain expertise. This report presents a comprehensive analysis covering technical feasibility, financial viability, market assessment, and risk evaluation.

### Project Highlights
| Parameter | Details |
|-----------|---------|
| Project Name | {name} |
| Nature of Business | {btype.title()} |
| Location | {loc_full} |
| Products/Services | {products} |
| Total Project Cost | {total_cost} |
| Promoter's Contribution | {contribution} |
| Term Loan Required | {term_loan} |
| Expected Annual Revenue | {revenue} |
| Employment Generation | {employees} persons |

### Key Strengths
- **Strong Market Demand**: The {btype} sector is witnessing robust growth, driven by increasing consumer demand and favorable government policies.
- **Strategic Location**: {loc_full} provides excellent connectivity, availability of raw materials, and access to skilled labor.
- **Experienced Promoter**: {promoter} brings relevant industry expertise and management capabilities to drive the project's success.
- **Financial Viability**: The project demonstrates strong returns with a projected payback period of 3-4 years and healthy profit margins.

### Conclusion
The project is technically feasible, financially viable, and economically justified. We recommend the financial institution to consider the proposal favorably for term loan assistance of **{term_loan}**."""

    ext1 = f"""

### Investment Rationale
The proposed investment in {name} is justified by several compelling factors:

1. **Growing Market**: The Indian {btype} market is projected to grow at 12-15% CAGR over the next five years, creating substantial opportunities for new entrants with quality offerings.
2. **Government Push**: Initiatives such as Make in India, Atmanirbhar Bharat, and sector-specific PLI schemes offer significant incentives including capital subsidies, tax benefits, and preferential credit access.
3. **Import Substitution**: There exists a significant opportunity to replace imported products with domestically manufactured alternatives, capturing value within the Indian economy.
4. **Employment Generation**: The project will create {employees} direct jobs and an estimated 2-3x indirect employment opportunities, contributing to local economic development.
5. **Technology Readiness**: Proven, commercially available technology reduces execution risk while ensuring consistent product quality.

### Key Financial Indicators
| Indicator | Value | Assessment |
|-----------|-------|------------|
| Internal Rate of Return (IRR) | 32% | Excellent — well above cost of capital |
| Net Present Value (NPV) | Positive | Project adds significant value |
| Debt Service Coverage Ratio | 2.5x | Strong — exceeds minimum 1.5x requirement |
| Return on Equity (ROE) | 35-40% | Outstanding returns for promoter |
| Payback Period | 3.2 years | Quick capital recovery |
| Break-Even Point | 52% capacity | Low risk — achieved in Year 1 |"""

    ext2 = f"""

### Socio-Economic Impact Assessment
The establishment of {name} at {loc_full} will generate significant positive socio-economic impact:

#### Direct Economic Benefits
- **Employment**: {employees} direct skilled and semi-skilled jobs with competitive wages
- **Revenue Generation**: Expected annual turnover of {revenue} contributing to regional GDP
- **Tax Contribution**: Direct and indirect taxes estimated at 15-20% of revenue
- **Supply Chain Development**: Procurement from local vendors worth ₹30-40 lakhs annually

#### Indirect Benefits
- Development of ancillary industries and service providers in the region
- Skill development and training of local workforce
- Infrastructure improvement in the surrounding area
- Increased economic activity and multiplier effects

#### Environmental Compliance
The project will adhere to all environmental regulations:
- Obtained/will obtain necessary clearances from State Pollution Control Board
- Implementation of waste management and recycling systems
- Use of energy-efficient machinery and processes
- Green energy integration (solar panels for auxiliary power)

### Alignment with Government Schemes
| Scheme | Benefit | Status |
|--------|---------|--------|
| PMEGP | Margin money subsidy 15-35% | Eligible |
| MSME Registration | Priority sector lending | Applied |
| State Industrial Policy | Capital subsidy up to 25% | Eligible |
| Skill India | Training subsidy | Applicable |
| Stand-Up India | Preferential interest rates | Under review |"""

    ext3 = f"""

### Detailed Sensitivity Analysis
The project's financial resilience has been tested under various adverse scenarios:

#### Scenario 1: Revenue Decline of 15%
Even with a 15% reduction in projected revenues, the project maintains a DSCR above 1.8x and achieves break-even by end of Year 1. Net profit margins reduce from 31% to approximately 22%, still ensuring adequate returns.

#### Scenario 2: Raw Material Cost Increase of 20%
With a 20% increase in raw material costs, the project's gross margins decline from 55% to 45%. However, through operational efficiency measures and selective price adjustments, net profitability remains positive at 18-20%.

#### Scenario 3: Delayed Capacity Utilization
If capacity utilization reaches only 50% in Year 1 (vs. projected 60%), the project still achieves cash break-even and can service debt obligations. Full recovery is achieved by Year 2 with accelerated capacity ramp-up.

#### Scenario 4: Interest Rate Increase of 2%
An increase of 200 basis points in the lending rate impacts annual interest costs by approximately ₹3-4 lakhs. The project's strong cash flows absorb this impact with minimal effect on overall viability.

| Scenario | Revenue Impact | DSCR | Break-Even | NPV Status |
|----------|---------------|------|------------|------------|
| Base Case | 0% | 2.5x | Year 1 | Positive |
| Revenue -15% | -15% | 1.8x | Year 1 | Positive |
| Cost +20% | 0% | 2.0x | Year 1 | Positive |
| Delayed CU | -10% | 1.7x | Year 1 | Positive |
| Rate +2% | 0% | 2.3x | Year 1 | Positive |"""

    ext4 = f"""

### Competitive Positioning Strategy
The project's competitive strategy is built on four pillars:

#### 1. Quality Leadership
Implementation of ISO 9001:2015 quality management system from inception. Every batch undergoes rigorous testing with documented quality certificates. This positions {name} as a trusted supplier for institutional and B2B segments.

#### 2. Cost Efficiency
Through lean manufacturing principles, automated processes where feasible, and strategic procurement, the project targets 10-15% cost advantage over comparable producers. This translates to either competitive pricing or superior margins.

#### 3. Customer Intimacy
A dedicated customer relationship management system will ensure rapid response to inquiries, customized solutions, and proactive after-sales support. Target: 90%+ customer retention rate.

#### 4. Innovation Focus
Annual allocation of 3-5% of revenue towards R&D and product innovation. This ensures continuous improvement in product quality, new product development, and process optimization.

### Implementation Milestones
| Phase | Activity | Timeline | Investment |
|-------|----------|----------|------------|
| Phase 1 | Land acquisition & approvals | Month 1-2 | ₹15,00,000 |
| Phase 2 | Civil construction | Month 2-5 | ₹20,00,000 |
| Phase 3 | Equipment procurement | Month 3-6 | {machinery_cost} |
| Phase 4 | Installation & commissioning | Month 5-7 | ₹5,00,000 |
| Phase 5 | Trial production | Month 7-8 | ₹3,00,000 |
| Phase 6 | Commercial operations | Month 9 | Working capital |

### Risk Summary Matrix
| Risk Factor | Probability | Impact | Mitigation |
|------------|-------------|--------|------------|
| Market demand shortfall | Low | High | Diversified customer base |
| Raw material price volatility | Medium | Medium | Long-term supplier contracts |
| Technology obsolescence | Low | Medium | Modular, upgradeable systems |
| Regulatory changes | Low | Low | Proactive compliance |
| Competition intensity | Medium | Medium | Quality & cost leadership |"""

    sections_content["executive_summary"] = base + (ext1 if pages_per_section >= 1.5 else "") + (ext2 if pages_per_section >= 2.5 else "") + (ext3 if pages_per_section >= 4 else "") + (ext4 if pages_per_section >= 6 else "")

    # ─── PROMOTER PROFILE ──────────────────────────
    base = f"""## Promoter & Company Profile

### Promoter Details
| Parameter | Details |
|-----------|---------|
| Name | {promoter} |
| Qualification | {qualification} |
| Experience | {experience} |
| Role | Managing Director / Proprietor |

### Competence & Background
{promoter} has demonstrated strong entrepreneurial capabilities and possesses the necessary technical knowledge and management skills to successfully execute and operate the proposed project. The promoter has established a track record of integrity and financial discipline, with a clean credit history.

### Company Structure
| Aspect | Details |
|--------|---------|
| Entity Type | Private Limited Company / Proprietorship |
| Registered Office | {loc_full} |
| Year of Incorporation | 2024 |
| Industry Sector | {btype.title()} |
| CIN / Registration | Applied / Under process |

### Management Team
The project will be managed by an experienced team comprising:
- **Managing Director / Proprietor**: {promoter} — Overall strategy and operations
- **Operations Manager**: Responsible for day-to-day production and quality control
- **Finance & Accounts Manager**: Financial planning, compliance, and reporting
- **Marketing Manager**: Sales strategy, customer acquisition, and market development

### Vision & Mission
**Vision**: To become a leading {btype} enterprise recognized for quality, innovation, and customer satisfaction.

**Mission**: To deliver exceptional {products} while maintaining the highest standards of quality, sustainability, and stakeholder value creation."""

    ext1 = f"""

### Promoter's Track Record
{promoter}'s credentials and achievements relevant to this project include:

1. **Educational Background**: {qualification} — providing a solid foundation in business management, technical aspects, and strategic thinking necessary for enterprise development.
2. **Professional Experience**: {experience} — demonstrating hands-on knowledge of industry dynamics, supply chain management, quality control processes, and customer relationship management.
3. **Financial Discipline**: Clean credit record with no defaults or settlements. All existing financial obligations are current and well-managed.
4. **Networking**: Established relationships with suppliers, distributors, and industry associations that will facilitate business development.
5. **Local Knowledge**: Deep understanding of {loc_full}'s business environment, regulatory requirements, and market opportunities.

### Organizational Development Plan
| Year | Milestone | Team Size |
|------|-----------|-----------|
| Year 1 | Foundation — Core operations team | {employees} |
| Year 2 | Expansion — Add sales and support | {int(int(employees) * 1.3) if employees.isdigit() else employees} |
| Year 3 | Growth — Quality & R&D team | {int(int(employees) * 1.6) if employees.isdigit() else employees} |
| Year 4 | Maturity — Full management structure | {int(int(employees) * 2) if employees.isdigit() else employees} |

### Corporate Governance Framework
The company will implement robust governance practices:
- Regular board meetings (minimum quarterly)
- Annual statutory audits by qualified chartered accountants
- Compliance with all applicable laws including Companies Act, GST, Labour Laws
- Implementation of internal control systems and standard operating procedures
- Transparent financial reporting to all stakeholders including lending institutions"""

    ext2 = f"""

### Detailed Department Structure

#### Production Department
- Production Manager (1) — Overall production planning and supervision
- Quality Control Inspector (1) — Quality assurance and testing
- Machine Operators ({int(int(employees)*0.4) if employees.isdigit() else '8'}) — Equipment operation and monitoring
- Helpers ({int(int(employees)*0.3) if employees.isdigit() else '6'}) — Machine support and material handling

#### Administration & Finance
- Accountant (1) — Book-keeping, tax compliance, and financial reporting
- Office Assistant (1) — Administrative support and documentation
- HR Executive (1) — Recruitment, training, and employee welfare

#### Sales & Marketing
- Sales Manager (1) — Customer acquisition and relationship management
- Marketing Executive (1) — Digital marketing, branding, and promotions
- Field Sales Representatives (2) — Direct sales and distributor management

### Employee Compensation Structure
| Category | Number | Monthly CTC/Person | Annual Cost |
|----------|--------|-------------------|-------------|
| Management | 3 | ₹50,000 | ₹18,00,000 |
| Technical Staff | 5 | ₹25,000 | ₹15,00,000 |
| Skilled Workers | {int(int(employees)*0.4) if employees.isdigit() else '8'} | ₹18,000 | ₹17,28,000 |
| Semi-skilled | {int(int(employees)*0.3) if employees.isdigit() else '6'} | ₹12,000 | ₹8,64,000 |
| **Total** | **{employees}** | | **₹58,92,000** |"""

    sections_content["promoter_profile"] = base + (ext1 if pages_per_section >= 1.5 else "") + (ext2 if pages_per_section >= 2.5 else "")

    # ─── INDUSTRY OVERVIEW ──────────────────────────
    base = f"""## Industry & Market Analysis

### Industry Overview
The {btype} sector in India is experiencing significant growth, supported by favorable government initiatives such as Make in India, Startup India, and Atmanirbhar Bharat. The sector is projected to grow at a CAGR of 12-15% over the next five years.

### Market Size & Trends
- The domestic market for {products} has been expanding steadily at 10-15% annually
- Increasing urbanization and rising disposable incomes are driving demand
- Government infrastructure development programs are creating new market opportunities
- Digital transformation and e-commerce are opening new distribution channels

### Target Market Analysis
| Segment | Market Share | Growth Rate | Strategy |
|---------|-------------|-------------|----------|
| Domestic B2B | 40% | 12% | Direct sales & partnerships |
| Domestic B2C | 30% | 15% | E-commerce & dealer network |
| Institutional | 20% | 10% | Tender & contract bidding |
| Export | 10% | 18% | Trade fairs & export houses |

### Competitive Landscape
The market presents healthy competition with opportunities for new entrants who can offer:
- Competitive pricing through efficient operations
- Superior quality and consistency
- Timely delivery and reliable supply chain
- Innovation in product design and features

### Demand-Supply Analysis
The current demand for {products} in the region exceeds supply, creating a favorable market entry opportunity. The project's capacity of {capacity} is well-positioned to capture approximately 5-8% of the regional market share within the first three years.

### Government Support
- MSME subsidies and credit guarantee schemes
- State industry promotion policies and tax incentives
- Skill development and training support programs
- Technology upgradation fund schemes (TUFS)"""

    ext1 = f"""

### Macro-Economic Environment
India's GDP growth trajectory of 6-7% provides a strong macroeconomic backdrop for the {btype} sector. Key economic indicators favorable to this project include:

| Indicator | Current | Projected (5-Year) | Impact on Project |
|-----------|---------|-------------------|-------------------|
| GDP Growth | 6.5% | 7.0% | Positive — rising demand |
| Industrial Production | 5.2% | 8.0% | Positive — sector expansion |
| Inflation (CPI) | 5.5% | 4.5% | Neutral — stable input costs |
| Interest Rates | 10-12% | 9-11% | Positive — lower borrowing costs |
| Exchange Rate | Stable | Gradual depreciation | Positive — export competitiveness |

### Customer Segmentation Analysis
The target customer base for {products} can be segmented as follows:

#### Segment A: Large Industrial Buyers (25% of revenue)
- Annual purchase volume: High
- Purchase frequency: Monthly/Quarterly contracts
- Key decision factors: Quality consistency, timely delivery, competitive pricing
- Acquisition strategy: Direct sales team, industry exhibitions, referral programs

#### Segment B: Small & Medium Enterprises (35% of revenue)
- Annual purchase volume: Medium
- Purchase frequency: As-needed basis
- Key decision factors: Price competitiveness, flexible order quantities, quick turnaround
- Acquisition strategy: Dealer network, online presence, trade directories

#### Segment C: Retail / End Consumer (25% of revenue)
- Annual purchase volume: Low per customer, high aggregate
- Purchase frequency: Periodic
- Key decision factors: Brand reputation, quality, availability
- Acquisition strategy: E-commerce, retail partnerships, social media marketing

#### Segment D: Government & Institutional (15% of revenue)
- Annual purchase volume: High (bulk orders)
- Purchase frequency: Annual contracts via tenders
- Key decision factors: Compliance, certification, competitive L1 pricing
- Acquisition strategy: GeM portal registration, tender participation"""

    ext2 = f"""

### Regional Market Deep-Dive: {state if state else 'India'}
The {state if state else 'national'} market for {btype} products presents significant opportunities:

#### Market Size Estimation
- State/regional market size: ₹500-800 Cr (estimated)
- Addressable market for {name}: ₹50-80 Cr
- Target market capture (Year 3): 5-8% = ₹2.5-6.4 Cr

#### Key Competitors Analysis
| Competitor | Market Share | Strengths | Weaknesses |
|------------|-------------|-----------|------------|
| Established Player A | 25% | Brand recognition, distribution | High pricing, slow innovation |
| Established Player B | 20% | Wide product range | Quality inconsistency |
| Regional Player C | 15% | Local presence | Limited capacity |
| Unorganized Sector | 30% | Low pricing | Poor quality, no certification |
| **{name} (Projected)** | **5-8%** | **Quality + competitive pricing** | **New entrant** |

#### Market Entry Strategy
Phase 1 (Month 1-6): Establish presence in {loc_full} and surrounding areas. Focus on B2B customers through direct sales. Target: 20 active customers.

Phase 2 (Month 7-12): Expand to {state if state else 'neighboring districts'}. Launch dealer appointment program. Target: 50 active customers.

Phase 3 (Year 2): Pan-regional coverage. E-commerce integration. Government tender participation. Target: 100+ active customers.

### Pricing Strategy
| Category | Market Average | Our Price | Advantage |
|----------|---------------|-----------|-----------|
| Premium Range | 100% | 90-95% | 5-10% below market |
| Standard Range | 100% | 85-90% | 10-15% below market |
| Economy Range | 100% | 95% | Quality premium |"""

    sections_content["industry_overview"] = base + (ext1 if pages_per_section >= 1.5 else "") + (ext2 if pages_per_section >= 2.5 else "")

    # ─── PRODUCT DETAILS, TECHNICAL, COST, PROFIT, SWOT, RISK, CONCLUSION ───
    # (Similar pattern for remaining sections)

    base_product = f"""## Product / Service Details

### Product Portfolio
**Primary Products/Services**: {products}

### Product Specifications
The products will be manufactured/delivered to meet Indian and international quality standards, ensuring:
- Compliance with Bureau of Indian Standards (BIS) specifications
- Quality management systems (ISO 9001:2015 certification planned)
- Environmental compliance as per CPCB norms

### Quality Control Framework
| Stage | Activity | Responsibility |
|-------|----------|---------------|
| Incoming | Raw material inspection & testing | QC Inspector |
| In-Process | Stage-wise quality checks | Production Manager |
| Final | Finished product testing & certification | QC Inspector |
| Post-Sales | Customer feedback & corrective action | Sales Manager |

### Unique Selling Propositions (USPs)
- **Quality Assurance**: Rigorous quality control at every stage
- **Competitive Pricing**: Cost-efficient production methods ensuring 10-15% price advantage
- **Customization**: Ability to customize products as per client requirements
- **Timely Delivery**: Robust supply chain and logistics management
- **After-Sales Support**: Dedicated customer service and support team"""

    ext1_product = f"""

### Detailed Product Specifications
| Parameter | Standard | Premium |
|-----------|----------|---------|
| Material Grade | IS Standard | High-grade / Imported |
| Tolerance | ±2% | ±0.5% |
| Finish | Standard | Superior finish |
| Certification | BIS | BIS + additional |
| Warranty | 6 months | 12 months |
| Packaging | Standard | Branded premium |

### Product Development Roadmap
| Timeline | Product/Feature | Expected Revenue Contribution |
|----------|----------------|------------------------------|
| Year 1 | Core product range | 100% of current revenue |
| Year 2 | Premium variants | Additional 15% revenue |
| Year 3 | Customized solutions | Additional 20% revenue |
| Year 4-5 | Export-grade products | Additional 15% revenue |

### Raw Material Requirements
Primary raw materials: {raw_materials}

| Material | Source | Monthly Quantity | Monthly Cost |
|----------|--------|-----------------|-------------|
| Primary Raw Material | Local suppliers | As per production plan | 35% of COGS |
| Secondary Materials | Regional vendors | As needed | 15% of COGS |
| Packaging Material | Specialized vendors | Based on output | 8% of COGS |
| Consumables | Local market | Standard quantities | 5% of COGS |"""

    sections_content["product_details"] = base_product + (ext1_product if pages_per_section >= 1.5 else "")

    base_tech = f"""## Technical Feasibility & Production

### Technology Selection
The project will employ modern, proven technology sourced from reputed manufacturers. The production process is designed for optimal efficiency, minimal waste, and consistent quality.

### Production Capacity
| Parameter | Details |
|-----------|---------|
| Installed Capacity | {capacity} |
| Year 1 Utilization | 60% of installed capacity |
| Year 2 Utilization | 75% of installed capacity |
| Year 3+ Utilization | 85-90% of installed capacity |

### Infrastructure Requirements
| Component | Specification |
|-----------|--------------|
| Land Area | {land_area} |
| Building Area | {building_area} |
| Power Supply | 3-phase industrial connection |
| Water Supply | Municipal + borewell backup |
| Manpower | {employees} persons |

### Plant & Machinery
Major machinery and equipment will be procured from reputed manufacturers with warranties and AMC. Estimated cost: **{machinery_cost}**.

### Production Process Flow
1. **Raw Material Procurement** → Quality inspection and storage
2. **Pre-Processing** → Material preparation and conditioning
3. **Main Processing** → Core production/manufacturing
4. **Quality Testing** → In-process and final quality verification
5. **Finishing** → Final processing, grading, and sorting
6. **Packaging** → Professional packaging and labeling
7. **Dispatch** → Storage, logistics, and delivery

### Utilities & Services
| Utility | Specification | Monthly Cost |
|---------|--------------|-------------|
| Power | 50-100 KW with DG backup | ₹40,000-60,000 |
| Water | 5,000 liters/day | ₹5,000-8,000 |
| Fuel | As required | ₹10,000-15,000 |"""

    ext1_tech = f"""

### Detailed Machinery List
| Sr. | Equipment | Quantity | Make | Cost (₹) |
|-----|-----------|----------|------|----------|
| 1 | Primary Processing Machine | 2 | Reputed Indian | 8,00,000 |
| 2 | Secondary Processing Unit | 1 | Reputed Indian | 5,00,000 |
| 3 | Quality Testing Equipment | 1 Set | Imported/Indian | 3,00,000 |
| 4 | Packaging Machine | 1 | Indian Make | 2,50,000 |
| 5 | Material Handling Equipment | 1 Set | Indian Make | 1,50,000 |
| 6 | Weighing & Measuring | 1 Set | Calibrated Standard | 1,00,000 |
| 7 | Auxiliary Equipment | 1 Lot | Various | 2,00,000 |
| 8 | Electrical Installation | 1 Lot | Standard | 1,50,000 |
| | **Total Machinery Cost** | | | **{machinery_cost}** |

### Building Layout Plan
The factory building at {loc_full} will be organized as follows:
- **Production Hall**: 60% of building area — housing all production machinery
- **Raw Material Storage**: 15% — climate-controlled storage for raw materials
- **Finished Goods Store**: 10% — organized storage with FIFO system
- **Quality Lab**: 5% — testing and inspection area
- **Office & Admin**: 5% — management offices and meeting room
- **Utilities Area**: 5% — DG set, compressor, water treatment"""

    sections_content["technical_details"] = base_tech + (ext1_tech if pages_per_section >= 1.5 else "")

    base_cost = f"""## Project Cost & Means of Finance

### Total Project Cost
| Sr. No. | Particulars | Amount (₹) |
|---------|------------|------------|
| 1 | Land & Site Development | {land_cost_f} |
| 2 | Building & Civil Works | {building_cost_f} |
| 3 | Plant & Machinery | {machinery_cost} |
| 4 | Misc. Fixed Assets | {misc_assets_f} |
| 5 | Pre-operative Expenses | {preop_cost_f} |
| 6 | Contingency | {contingency_f} |
| 7 | Working Capital Margin | {wc_margin_f} |
| | **Total Project Cost** | **{total_cost}** |

### Means of Finance
| Sr. No. | Source | Amount (₹) | % Share |
|---------|--------|------------|---------|
| 1 | Promoter's Equity Contribution | {contribution} | {pc_pct}% |
| 2 | Term Loan from Bank | {term_loan} | {tl_pct}% |
| | **Total** | **{total_cost}** | **100%** |

### Term Loan Details
| Parameter | Details |
|-----------|---------|
| Loan Amount | {term_loan} |
| Interest Rate | 10-12% per annum |
| Repayment Period | 7 years (incl. 1 year moratorium) |
| Moratorium | 12 months from first disbursement |
| Repayment | 24 quarterly installments after moratorium |
| Security | First charge on all fixed assets |

### Working Capital Assessment
| Component | Days | Amount (₹) |
|-----------|------|------------|
| Raw Material Inventory | 30 days | Calculated |
| Work-in-Progress | 15 days | Calculated |
| Finished Goods | 15 days | Calculated |
| Receivables | 30 days | Calculated |
| Less: Creditors | 30 days | Calculated |
| **Net Working Capital** | | **{working_capital}** |"""

    ext1_cost = f"""

### Pre-Operative Expenses Breakdown
| Item | Amount (₹) |
|------|------------|
| Company Registration & Legal | {_format_inr(round(preop_cost * 0.20))} |
| Project Report & Consultancy | {_format_inr(round(preop_cost * 0.35))} |
| Environmental & Fire NOC | {_format_inr(round(preop_cost * 0.10))} |
| Factory License & Permits | {_format_inr(round(preop_cost * 0.10))} |
| Trial Run Expenses | {_format_inr(round(preop_cost * 0.15))} |
| Insurance & Others | {_format_inr(round(preop_cost * 0.10))} |
| **Total Pre-Operative** | **{preop_cost_f}** |

### Loan Repayment Schedule
| Year | Principal (₹) | Interest (₹) | Total Payment (₹) | Outstanding (₹) |
|------|---------------|-------------|-------------------|-----------------| 
| Year 1 | Moratorium | {term_loan} interest | Interest only | {term_loan} |
| Year 2 | Quarterly EMI | Reducing | As per schedule | Reducing |
| Year 3 | Quarterly EMI | Reducing | As per schedule | Reducing |
| Year 4 | Quarterly EMI | Reducing | As per schedule | Reducing |
| Year 5 | Quarterly EMI | Reducing | As per schedule | Reducing |
| Year 6 | Quarterly EMI | Reducing | As per schedule | Reducing |
| Year 7 | Final installment | Minimal | Final payment | Nil |

### Depreciation Schedule
| Asset Category | Rate (%) | Method |
|---------------|----------|--------|
| Building | 5% | Written Down Value |
| Plant & Machinery | 15% | Written Down Value |
| Furniture & Fixtures | 10% | Written Down Value |
| Vehicles | 15% | Written Down Value |
| Computer & Software | 40% | Written Down Value |"""

    sections_content["project_cost"] = base_cost + (ext1_cost if pages_per_section >= 1.5 else "")

    base_profit = f"""## Profitability & Financial Projections

### Revenue Projections (5-Year)
| Year | Capacity Utilization | Annual Revenue (₹) | Growth % |
|------|---------------------|-------------------|----------|
| Year 1 | 60% | {revenue} | — |
| Year 2 | 75% | 125% of Year 1 | 25% |
| Year 3 | 85% | 142% of Year 1 | 13% |
| Year 4 | 90% | 167% of Year 1 | 18% |
| Year 5 | 90% | 183% of Year 1 | 10% |

### Projected Profit & Loss Statement
| Particulars | Year 1 | Year 2 | Year 3 |
|-------------|--------|--------|--------|
| Revenue | {revenue} | +25% | +38% |
| Raw Material Cost | 35% of revenue | 35% | 34% |
| Staff Salaries | 16% of revenue | 14% | 14% |
| Admin & Selling Exp. | 8% of revenue | 7% | 7% |
| Interest on Loan | Per schedule | Reducing | Reducing |
| Depreciation | As per rates | As per rates | As per rates |
| **Net Profit %** | **31%** | **36%** | **38%** |

### Key Financial Ratios
| Ratio | Value | Benchmark |
|-------|-------|-----------|
| Gross Profit Margin | 55-60% | Above 40% ✅ |
| Net Profit Margin | 31-38% | Above 15% ✅ |
| Return on Investment | 28-35% | Above 20% ✅ |
| DSCR | 2.5x - 3.5x | Above 1.5x ✅ |
| IRR | 32% | Above 15% ✅ |
| Payback Period | 3.2 years | Below 5 years ✅ |

### Break-Even Analysis
- **Break-Even Sales**: 52% of capacity
- **Break-Even Revenue**: Approx. ₹78,50,000 per annum
- The project achieves break-even well within Year 1, demonstrating low business risk."""

    ext1_profit = f"""

### Detailed Year-wise Profitability
| Particulars | Year 1 (₹) | Year 2 (₹) | Year 3 (₹) | Year 4 (₹) | Year 5 (₹) |
|-------------|-----------|-----------|-----------|-----------|-----------|
| Gross Revenue | 100% | 125% | 142% | 167% | 183% |
| Less: Returns & Discounts | 2% | 2% | 1.5% | 1.5% | 1% |
| Net Revenue | 98% | 123% | 140% | 165% | 182% |
| Cost of Goods Sold | 35% | 43% | 48% | 55% | 60% |
| **Gross Profit** | **63%** | **80%** | **92%** | **110%** | **122%** |
| Operating Expenses | 18% | 20% | 22% | 24% | 26% |
| EBITDA | 45% | 60% | 70% | 86% | 96% |
| Depreciation | Standard | Standard | Standard | Standard | Standard |
| Interest | As schedule | Reducing | Reducing | Reducing | Reducing |
| **PBT** | **Healthy** | **Growing** | **Strong** | **Excellent** | **Outstanding** |

### Cash Flow Projections
The project generates positive cash flows from Year 1 onwards, ensuring comfortable debt servicing and adequate surplus for reinvestment:

- **Year 1**: Operating cash flow covers 100% of debt service obligations with comfortable surplus
- **Year 2**: Cash surplus increases by 25-30% enabling working capital self-financing
- **Year 3**: Significant cash generation allowing promoter dividend distribution
- **Year 4-5**: Full debt repayment trajectory with growing free cash flow

### Return on Equity Analysis
| Year | Equity Base | Net Profit | ROE % |
|------|-----------|-----------|-------|
| Year 1 | {contribution} | Growing | 25-30% |
| Year 2 | Growing | Higher | 35-40% |
| Year 3 | Growing | Strong | 40-45% |"""

    sections_content["profitability"] = base_profit + (ext1_profit if pages_per_section >= 1.5 else "")

    base_swot = f"""## SWOT Analysis

### Strengths
- ✅ **Experienced Promoter**: {promoter} brings deep domain expertise and industry contacts
- ✅ **Strategic Location**: {loc_full} offers excellent infrastructure, connectivity, and market access
- ✅ **Growing Market**: Strong and sustained demand for {products}
- ✅ **Modern Technology**: State-of-the-art machinery ensuring efficiency and quality
- ✅ **Financial Viability**: Strong projected ROI of 28-35% with payback within 3.2 years
- ✅ **Lean Operations**: Optimized cost structure with competitive pricing capability
- ✅ **Quality Focus**: ISO-grade quality management from inception
- ✅ **Government Support**: Eligible for multiple MSME incentive schemes

### Weaknesses
- ⚠️ Initial phase challenges in building brand recognition and market presence
- ⚠️ Dependence on external suppliers for key raw materials
- ⚠️ New entrant in market with established competitors
- ⚠️ Working capital constraints during initial ramp-up phase
- ⚠️ Limited product diversification in early stages

### Opportunities
- 🚀 Rapidly expanding domestic market driven by India's economic growth (6-7% GDP)
- 🚀 Government initiatives (Make in India, MSME support) providing subsidies and tax benefits
- 🚀 E-commerce and digital marketing opening cost-effective national sales channels
- 🚀 Export potential to neighboring countries and international markets
- 🚀 Opportunity for backward/forward integration and value addition
- 🚀 Import substitution demand creating ready market for domestic production

### Threats
- ⚡ Competition from established players and new entrants
- ⚡ Raw material price volatility affecting margins
- ⚡ Economic slowdowns and market uncertainties
- ⚡ Regulatory and compliance changes impacting operations
- ⚡ Technology disruption requiring continuous upgradation

### SWOT Summary Matrix
| Factor | Rating | Impact |
|--------|--------|--------|
| Strengths | High | Positive — strong competitive position |
| Weaknesses | Manageable | Addressed through mitigation strategies |
| Opportunities | Significant | Growth potential 15-20% annually |
| Threats | Moderate | Managed through risk mitigation |"""

    ext1_swot = f"""

### Mitigation Strategies for Weaknesses

#### W1: Brand Building Strategy
- Digital presence: Professional website + social media (Instagram, LinkedIn, YouTube)
- Content marketing: Regular industry articles, case studies, and product demonstrations
- Trade exhibitions: Participation in 4-6 industry exhibitions annually
- Timeline: Brand awareness target of 30% in regional market by Year 2

#### W2: Supply Chain Risk Management
- Multiple vendor policy: Minimum 3 approved suppliers for each critical raw material
- Strategic inventory: 30-45 days buffer stock for critical materials
- Long-term contracts: Annual rate contracts with volume discounts
- Backward integration: Feasibility study for key raw material production by Year 3

#### W3: Competition Strategy
- Quality differentiation: ISO certification and consistent quality
- Price competitiveness: 10-15% cost advantage through lean manufacturing
- Customer service: 24-hour response time, dedicated relationship managers
- Innovation: Continuous product improvement with 3-5% R&D allocation

#### W4: Working Capital Management
- Working capital lending: Banking facility for operational needs
- Inventory optimization: Just-in-time for non-critical items
- Receivables management: 30-day credit policy with early payment incentives
- Creditor negotiation: Extended payment terms with major suppliers

### Opportunity Exploitation Plan
| Opportunity | Action Plan | Timeline | Expected Impact |
|------------|------------|----------|-----------------|
| E-commerce | Launch on Amazon, Flipkart, IndiaMART | Month 6 | +15% revenue |
| Exports | Registration with FIEO, participate in trade fairs | Year 2 | +10% revenue |
| Govt. tenders | GeM registration, tender preparation team | Month 3 | +15% revenue |
| Product expansion | R&D for premium variants | Year 2 | +20% revenue |"""

    sections_content["swot_analysis"] = base_swot + (ext1_swot if pages_per_section >= 1.5 else "")

    base_risk = f"""## Risk Assessment & Mitigation

### Risk Matrix
| Risk Category | Probability | Impact | Risk Level | Mitigation Strategy |
|--------------|------------|--------|------------|---------------------|
| Market Risk | Medium | High | Medium | Market diversification, competitive pricing |
| Financial Risk | Low | High | Low | Conservative projections, adequate working capital |
| Operational Risk | Low | Medium | Low | Experienced team, standard procedures |
| Technology Risk | Low | Medium | Low | Proven technology, AMC with suppliers |
| Regulatory Risk | Low | Medium | Low | Proactive compliance, professional advisors |
| Supply Chain Risk | Medium | Medium | Medium | Multiple suppliers, buffer inventory |
| HR Risk | Low | Low | Low | Competitive compensation, training programs |

### Detailed Risk Analysis

#### 1. Market Risk
- **Risk**: Lower than projected demand or pricing pressure
- **Probability**: Medium
- **Mitigation**: Market research-backed projections; diversified customer base across B2B, B2C, and institutional segments; flexible pricing strategy

#### 2. Financial Risk
- **Risk**: Cash flow constraints or inability to service debt
- **Probability**: Low
- **Mitigation**: Conservative revenue estimates (60% capacity in Year 1); adequate working capital provision; DSCR maintained above 2.0x

#### 3. Operational Risk
- **Risk**: Production disruptions or quality issues
- **Probability**: Low
- **Mitigation**: Experienced operations team; preventive maintenance schedule; ISO-quality processes; buffer stock of critical spares

#### 4. Competition Risk
- **Risk**: Increased competition affecting market share
- **Probability**: Medium
- **Mitigation**: Focus on quality differentiation; customer relationship management; continuous product improvement

### Insurance Coverage
| Type | Coverage | Premium (Annual) |
|------|----------|-----------------|
| Fire & Allied Perils | Full asset value | ₹15,000-25,000 |
| Business Interruption | 6 months revenue | ₹10,000-15,000 |
| Product Liability | ₹50,00,000 | ₹8,000-12,000 |
| Workers Compensation | As per statute | ₹12,000-18,000 |
| **Total Insurance** | | **₹45,000-70,000** |"""

    ext1_risk = f"""

### Contingency Planning

#### Business Continuity Plan
The project includes a comprehensive business continuity plan:

1. **Data Backup**: All business data backed up daily to cloud storage
2. **Alternative Power**: DG set backup sufficient for 48 hours of continuous operation
3. **Alternate Suppliers**: Pre-qualified backup suppliers for all critical raw materials
4. **Key Person Insurance**: Coverage for promoter and key management personnel
5. **Emergency Fund**: Reserve fund equal to 2 months' fixed costs maintained in liquid assets

#### Force Majeure Provisions
- Natural disaster recovery plan with 30-day restart target
- Insurance coverage for fire, flood, earthquake, and Act of God events
- Contractual force majeure clauses with key customers and suppliers
- Government disaster relief scheme eligibility maintained

### Regulatory Compliance Checklist
| Regulation | Authority | Status | Renewal |
|------------|-----------|--------|---------|
| GST Registration | GST Department | Completed | Annual |
| Factory License | Inspector of Factories | Applied | Annual |
| Fire NOC | Fire Department | Applied | 3 years |
| MSME Registration | MSME Ministry | Completed | Lifetime |
| Environmental Consent | SPCB | Applied | 5 years |
| Trade License | Municipal Authority | Applied | Annual |
| Labour Licenses | Labour Department | Applied | Annual |
| BIS Certification | Bureau of Indian Standards | Planned | Annual |"""

    sections_content["risk_assessment"] = base_risk + (ext1_risk if pages_per_section >= 1.5 else "")

    # ─── CONTACT DETAILS ─────────────────────────────
    base_contact = f"""## Contact Details

### Promoter / Authorized Signatory
| Parameter | Details |
|-----------|---------|
| Name | {promoter} |
| Designation | Managing Director / Proprietor |
| Qualification | {qualification} |

### Business Contact Information
| Parameter | Details |
|-----------|---------|
| Business Name | {name} |
| Registered Address | {contact_address} |
| Phone / Mobile | {contact_phone if contact_phone else 'To be provided'} |
| Email | {contact_email if contact_email else 'To be provided'} |
| Website | {contact_website if contact_website else 'N/A'} |

### Statutory Details
| Registration | Details |
|-------------|---------|
| GST Number | {contact_gst if contact_gst else 'Applied / Under process'} |
| PAN | {contact_pan if contact_pan else 'Available on request'} |
| MSME Registration | Udyam registered / Applied |
| Factory License | Applied / Under process |

### Bank Details
| Parameter | Details |
|-----------|---------|
| Bank Name | To be provided |
| Branch | {loc_full} |
| Account Type | Current Account |
| IFSC Code | To be provided |

### Project Site Address
{contact_address}
{f'{district}, ' if district else ''}{state if state else ''}"""

    sections_content["contact_details"] = base_contact

    base_conclusion = f"""## Conclusion & Recommendations

### Project Summary
The proposed project of **{name}** for {products} at {loc_full} is a well-conceived business venture that addresses a genuine market need. The comprehensive analysis presented in this DPR demonstrates the project's viability across all critical parameters.

### Viability Assessment

#### Technical Viability ✅
The project employs proven, modern technology with established production processes. The proposed capacity of {capacity} is aligned with market demand, and the phased capacity utilization plan (60% → 75% → 85%) is realistic and achievable.

#### Financial Viability ✅
| Parameter | Assessment |
|-----------|-----------|
| Total Investment | {total_cost} |
| Expected ROI | 28-35% — Excellent |
| DSCR | 2.5x - 3.5x — Well above minimum 1.5x |
| IRR | 32% — Significantly above cost of capital |
| Payback Period | 3.2 years — Quick capital recovery |
| Break-Even | 52% capacity — Achievable in Year 1 |

#### Market Viability ✅
Strong and growing demand for {products} with multiple customer segments. The promoter's industry experience and strategic location provide competitive advantages.

#### Economic & Social Impact ✅
- Direct employment for **{employees}** persons
- Indirect employment generation through supply chain
- Contribution to local economic development at {loc_full}
- Tax revenue generation for the government

### Recommendation
Based on our thorough analysis of all project parameters — technical feasibility, market analysis, financial projections, risk assessment, and promoter capability — **we strongly recommend this project for financial assistance**.

The project is financially sound with strong profitability indicators, experienced promoter leadership, and a favorable risk profile. The term loan of **{term_loan}** is well-supported by projected cash flows with a DSCR consistently above 2.5x.

---
*This Detailed Project Report has been prepared by DPR Copilot AI. All financial projections are based on assumptions and estimates. Actual results may vary.*"""

    ext1_conclusion = f"""

### Strengths of the Proposal — Summary for Lender

1. **Strong Financials**: IRR of 32%, DSCR of 2.5x+, and break-even at just 52% capacity demonstrate low lending risk and comfortable debt servicing.

2. **Promoter Credibility**: {promoter} brings relevant qualifications ({qualification}) and meaningful experience ({experience}), ensuring competent project execution and operation.

3. **Market Opportunity**: The {btype} sector is growing at 12-15% CAGR, with specific demand for {products} in {loc_full} and surrounding regions providing clear revenue visibility.

4. **Adequate Security**: The project's fixed assets (land, building, machinery valued at approximately {total_cost}) provide adequate security coverage for the requested term loan of {term_loan}.

5. **Low Risk Profile**: Conservative capacity utilization assumptions, diversified customer base, proven technology, and comprehensive risk mitigation measures minimize downside risk.

### Key Compliance Commitments
The promoter hereby commits to:
- Timely submission of all stock and financial statements to the lending institution
- Utilization of loan funds strictly for the stated purpose
- Maintenance of adequate insurance coverage throughout the loan tenure
- No diversion of funds to non-project activities
- Transparent and timely communication with the lending institution on all material matters

### Declaration
The information contained in this Detailed Project Report is true and correct to the best of our knowledge. The financial projections are based on reasonable assumptions and market research. We undertake to implement the project as per the plan outlined in this report.

**{promoter}**
Managing Director / Proprietor
{name}
{loc_full}
Date: Current Date"""

    sections_content["conclusion"] = base_conclusion + (ext1_conclusion if pages_per_section >= 1.5 else "")

    return sections_content.get(section_key, f"## {SECTION_NAMES.get(section_key, section_key)}\n\nContent for this section will be generated upon request.")



def _generate_dpr_sync(
    report_id: str, project_id: str, inputs: dict, project_name: str, custom_instructions: str | None, target_pages: int = 30, selected_sections: list | None = None
):
    """Generate DPR — tries OpenAI first, falls back to templates if no quota."""
    from financial.models import generate_financial_data

    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    SyncSession = sessionmaker(bind=sync_engine)

    try:
        # Use selected sections or all sections
        sections_to_generate = selected_sections if selected_sections else FAST_SECTIONS
        # Validate: only allow known section keys
        sections_to_generate = [s for s in sections_to_generate if s in SECTION_NAMES]
        if not sections_to_generate:
            sections_to_generate = FAST_SECTIONS

        print(f"\n{'='*60}")
        print(f"[DPR] 🚀 Starting generation for: {project_name} ({target_pages} pages, {len(sections_to_generate)} sections)")
        print(f"{'='*60}")

        financial_data = generate_financial_data(inputs)
        generated_sections = {}
        total = len(sections_to_generate)
        use_template = False

        # Check if OpenAI API key is available
        api_key = settings.OPENAI_API_KEY
        client = None
        if not api_key or api_key.strip() == "":
            print("[DPR] ⚠️  No OPENAI_API_KEY set — using template mode")
            use_template = True
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"[DPR] ⚠️  OpenAI client init failed: {e} — using template mode")
                use_template = True

        # Adjust words per section based on actual section count
        for i, section_key in enumerate(sections_to_generate, 1):
            section_name = SECTION_NAMES.get(section_key, section_key)
            print(f"[DPR] ({i}/{total}) Generating: {section_name}...")

            if not use_template and client:
                # Try AI first
                input_lines = [f"• {k.replace('_', ' ').title()}: {v}" for k, v in inputs.items() if v and not k.startswith("_")]
                input_context = "\n".join(input_lines) if input_lines else "General business project"

                words_per = int(((target_pages - 3) * 300) / 10)
                prompt = f'Write the "{section_name}" section for a DPR.\n\nPROJECT: {project_name}\n{input_context}\n\nProfessional consultancy language. {words_per} words for this section. Include tables where relevant.'
                system = "You are an expert business consultant writing professional Detailed Project Reports (DPR) for banks and investors."

                result = _try_openai(client, prompt, system)
                if result is None:
                    print(f"[DPR] ⚠️  OpenAI quota exceeded — switching to template mode")
                    use_template = True
                else:
                    generated_sections[section_key] = result
                    print(f"[DPR] ✅ ({i}/{total}) {section_name} — {len(result)} chars [AI]")
                    continue

            # Template fallback
            content = _generate_template(section_key, inputs, project_name, target_pages)
            generated_sections[section_key] = content
            print(f"[DPR] ✅ ({i}/{total}) {section_name} — {len(content)} chars [Template]")

        # Save to database
        with SyncSession() as session:
            report = session.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
            if report:
                report.sections = generated_sections
                report.financial_data = financial_data
                report.status = "completed"

            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "completed"

            session.commit()

        mode = "Templates" if use_template else "AI"
        print(f"\n{'='*60}")
        print(f"[DPR] 🎉 COMPLETE! {len(generated_sections)} sections [{mode}]")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"[DPR] ❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            with SyncSession() as session:
                report = session.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
                if report:
                    report.status = "failed"
                session.commit()
        except Exception:
            pass
    finally:
        sync_engine.dispose()


# ─── Standard endpoints ────────────────────────────────

@router.get("/{report_id}")
async def get_report(report_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": str(report.id), "title": report.title, "status": report.status,
        "sections": report.sections, "financial_data": report.financial_data,
        "pdf_path": report.pdf_path, "pptx_path": report.pptx_path,
        "created_at": str(report.created_at), "updated_at": str(report.updated_at),
    }


@router.get("/project/{project_id}")
async def list_project_reports(project_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GeneratedReport).where(GeneratedReport.project_id == project_id).order_by(GeneratedReport.created_at.desc())
    )
    reports = result.scalars().all()
    return [{"id": str(r.id), "title": r.title, "status": r.status, "created_at": str(r.created_at)} for r in reports]


@router.put("/{report_id}/section")
async def update_section(report_id: str, req: SectionUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    sections = dict(report.sections) if report.sections else {}
    sections[req.section_key] = req.content
    report.sections = sections
    await db.flush()
    return {"message": "Section updated", "section_key": req.section_key}


@router.post("/{report_id}/regenerate-section")
async def regenerate_section(report_id: str, req: RegenerateSectionRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    proj_result = await db.execute(select(Project).where(Project.id == report.project_id))
    project = proj_result.scalar_one()
    inputs = dict(project.inputs) if project.inputs else {}

    # Try AI, fallback to template
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    section_name = SECTION_NAMES.get(req.section_key, req.section_key)
    input_lines = [f"• {k.replace('_', ' ').title()}: {v}" for k, v in inputs.items() if v and not k.startswith("_")]
    prompt = f'Rewrite the "{section_name}" section.\n\nPROJECT: {project.name}\n{chr(10).join(input_lines)}\n\n{req.instructions or ""}\n\n400-800 words, professional.'

    new_content = _try_openai(client, prompt, "Expert business consultant writing DPRs.")
    if new_content is None:
        new_content = _generate_template(req.section_key, inputs, project.name)

    sections = dict(report.sections) if report.sections else {}
    sections[req.section_key] = new_content
    report.sections = sections
    await db.flush()
    return {"section_key": req.section_key, "content": new_content}
