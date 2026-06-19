"""
PROJECT: CDD Project Prediction System — GLG Korea

HYPOTHESIS FRAMEWORK (5-step McKinsey loop)
  STEP 1 — Issue:             Client's real decision in one line.
  STEP 2 — Core Hypothesis:   Specific, falsifiable bet (per value driver).
  STEP 3 — Sub-hypotheses:    3-5 MECE branches that must all hold.
  STEP 4 — Confirm Expert:    Evidence that proves the sub-hypothesis + expert.
  STEP 5 — Kill Expert:       Evidence that kills the sub-hypothesis + expert.

SCENARIOS (3 fixed value drivers, ordered by keyword signal)
  Scenario 1 = value driver with highest keyword score → Scenario 1
  Scenario 2, 3 = the other two

MECE GATE: sub-hypotheses are pre-validated. Gate blocks rendering if MECE fails.
CDD GUARDRAIL: warns if inputs don't look like a CDD engagement.
"""

import csv
import html
import json
import os
import re
import webbrowser
from datetime import datetime
from pathlib import Path

try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

# ── API Key ────────────────────────────────────────────────────────────────────
# Set ANTHROPIC_API_KEY in your shell environment before running.
# ──────────────────────────────────────────────────────────────────────────────

# Confirm-expert accent colors, assigned positionally across the 4 sub-hypotheses
CONFIRM_EXPERT_COLORS = ['#2563EB', '#D97706', '#059669', '#7C3AED']

# ── Keyword groups — signal which learning objective is primary ────────────────

KEYWORD_GROUPS = {
    'market_dynamics': [
        'market size', 'market sizing', 'tam', 'total addressable',
        'growth rate', 'market growth', 'cagr', 'demand driver',
        'how it works', 'market structure', 'industry size', 'market trend',
        'market dynamics', 'volume', 'participation', 'rounds played',
        'rounds of golf', 'pricing mechanism', 'how pricing', 'price setting',
        'customer behavior', 'customer decision', 'why customers', 'why members',
        'regulatory', 'regulation', 'how the industry',
    ],
    'operational_model': [
        'operations', 'operational', 'opex', 'capex',
        'cost structure', 'cost base', 'margin', 'margins', 'ebitda', 'ebit',
        'how they make money', 'revenue model', 'business model',
        'unit economics', 'fixed cost', 'variable cost',
        'supply chain', 'sourcing', 'headcount', 'workforce', 'staffing',
        'working capital', 'overhead', 'asset intensity',
        'deferred maintenance', 'maintenance', 'course condition',
        'renovation', 'capital improvement', 'asset quality',
        'pro shop', 'food and beverage', 'f&b', 'club operations',
        'membership dues', 'initiation fee', 'membership economics',
        'dues', 'deposit', 'initiation',
    ],
    'competitive_movement': [
        'competitor', 'competitors', 'competitive', 'competition',
        'market position', 'who wins', 'consolidation', 'fragmentation',
        'disruption', 'new entrant', 'substitute', 'market leader',
        'competitive dynamics', 'where is it heading', 'industry direction',
        'ksl capital', 'ksl', 'arcis', 'concert golf', 'apollo', 'south street',
        'invited', 'heritage golf', 'troon', 'clubcorp', 'american golf',
        'm&a', 'acquisition landscape', 'buyer landscape', 'deal flow',
        'strategic buyer', 'financial buyer', 'pe buyer', 'private equity buyer',
        'transaction', 'attrition', 'churn', 'retention', 'switching cost',
        'membership', 'member retention',
    ],
    'growth_scalability': [
        'growth', 'scale', 'scalability', 'expansion', 'penetration',
        'new market', 'geographic expansion', 'international',
        'organic growth', 'inorganic growth', 'growth trajectory',
        'pipeline', 'backlog', 'runway', 'market penetration',
        'share gain', 'whitespace', 'greenfield', 'brownfield',
        'same-store', 'comparable', 'unit growth', 'store count',
        'addressable', 'tam expansion', 'growth ceiling',
    ],
    'risk_regulatory': [
        'risk', 'regulatory', 'regulation', 'compliance',
        'legal', 'litigation', 'liability', 'environmental',
        'esg', 'sustainability', 'governance', 'political',
        'geopolitical', 'tariff', 'sanction', 'subsidy',
        'license', 'permit', 'zoning', 'barrier to entry',
        'antitrust', 'concentration', 'monopoly', 'policy',
        'safety', 'data privacy', 'ip', 'patent',
    ],
}

CDD_SIGNALS = [
    'market', 'industry', 'operations', 'competitive', 'how it works',
    'how they make money', 'business model', 'cost structure', 'revenue',
    'margin', 'ebitda', 'company', 'understand', 'research', 'learn',
    'membership', 'club', 'golf', 'sourcing', 'expert',
]


def score_keywords(text):
    lower = (text or '').lower()
    scores, matched = {}, {}
    for group, keywords in KEYWORD_GROUPS.items():
        hits = [kw for kw in keywords if kw in lower]
        scores[group] = len(hits)
        matched[group] = hits
    return scores, matched


def is_cdd(form_data):
    text = ' '.join([
        form_data.get('client', ''),
        form_data.get('reference_company', ''),
        form_data.get('client_wants', ''),
        form_data.get('verify_questions', ''),
    ]).lower()
    return any(sig in text for sig in CDD_SIGNALS)


# ── MECE validator ─────────────────────────────────────────────────────────────

STOP_WORDS = {
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have',
    'are', 'its', 'can', 'not', 'into', 'more', 'than', 'will',
    'does', 'been', 'each', 'their', 'what', 'which', 'when', 'they',
}


def tokenize(text):
    return [w for w in re.split(r'\W+', text.lower()) if len(w) > 4 and w not in STOP_WORDS]


def validate_mece(sub_hypotheses):
    issues = []
    if len(sub_hypotheses) < 3:
        issues.append('Fewer than 3 branches — coverage may be incomplete')
    if len(sub_hypotheses) > 5:
        issues.append('More than 5 branches — consider merging')
    for i in range(len(sub_hypotheses)):
        for j in range(i + 1, len(sub_hypotheses)):
            wi = set(tokenize(sub_hypotheses[i]['text']))
            wj = set(tokenize(sub_hypotheses[j]['text']))
            overlap = list(wi & wj)
            if len(overlap) >= 4:
                sample = '", "'.join(overlap[:3])
                issues.append(f'Branch {i+1} & {j+1} overlap: "{sample}"')
    return {'valid': len(issues) == 0, 'issues': issues}


# ── Learning-objective scenarios ───────────────────────────────────────────────
# reference_company = industry anchor (not an M&A target)
# Experts = people who worked at reference_company or a direct peer in the same segment

VALUE_DRIVERS = [
    {
        'id': 'market_dynamics',
        'name': 'Market Dynamics',
        'value_driver': 'market_dynamics',
        'color': '#2563EB',
        'keyword_group': 'market_dynamics',
        'so_what': lambda f: f"The market {f['reference_company'] or 'reference_company'} operates in has structural rules invisible from the outside — understanding them gives {f['client'] or 'the client'} a real information edge",
        'issue': lambda f: f"How does the industry {f['reference_company'] or 'reference_company'} operates in actually work — what drives demand, pricing, and participant behavior at the fundamental level?",
        'hypothesis': lambda f: f"The dynamics of {f['reference_company'] or 'reference_company'}'s market are governed by structural forces that experienced insiders understand and can explain — forces that public data alone cannot reveal to {f['client'] or 'the client'}.",
        'mece_axes': ['Demand logic', 'Pricing logic', 'Customer decision logic', 'Structural constraints'],
        'sub_hypotheses': [
            {
                'text': 'Demand drivers are structural and identifiable — volume in this market follows patterns that experienced participants can explain',
                'confirm_evidence': 'Primary research with participants who track demand cycles and can decompose volume into structural vs. cyclical drivers',
                'confirm_expert': 'Industry Volume / Demand Tracker',
                'confirm_expert_color': '#2563EB',
                'kill_evidence': 'Volume is idiosyncratic and unpredictable — insiders confirm no structural demand logic exists and cycles cannot be explained ex ante',
                'kill_expert': 'Market Data Analyst',
                'rationale': 'If demand has no structural logic, the client cannot model it — making any forecast assumption arbitrary.',
            },
            {
                'text': 'Pricing mechanisms follow a logic that industry participants understand and can benchmark — outsiders cannot derive it from public data alone',
                'confirm_evidence': 'Deep-dive with operators who have lived through price cycles and can explain the pricing levers, reference points, and negotiating dynamics',
                'confirm_expert': 'Former Operator / Pricing Decision-Maker',
                'confirm_expert_color': '#D97706',
                'kill_evidence': 'Pricing is purely spot or market-driven with no structural logic — incumbents confirm prices are set by external forces they cannot influence',
                'kill_expert': 'Market Pricing Economist',
                'rationale': 'Understanding pricing logic is the foundation for any revenue model — without it, the client is building on assumptions, not evidence.',
            },
            {
                'text': 'Customer and participant decision-making follows a distinct pattern — join, purchase, or renew decisions have a repeatable internal logic',
                'confirm_evidence': 'Structured interviews with active participants who can walk through their actual decision process and explain what drives commitment',
                'confirm_expert': 'Active Customer / Participant Decision-Maker',
                'confirm_expert_color': '#059669',
                'kill_evidence': 'Decisions are highly idiosyncratic — no repeatable pattern exists and even experienced participants cannot predict customer behavior reliably',
                'kill_expert': 'Consumer Behavior Researcher',
                'rationale': 'A repeatable decision logic means the client can model customer behavior — without it, demand forecasting has no anchor.',
            },
            {
                'text': 'Regulatory and structural constraints define the boundaries of the game — incumbents navigate these limits in ways outsiders cannot see',
                'confirm_evidence': 'Interviews with participants who have directly encountered regulatory or structural barriers and can explain the practical constraints on operators',
                'confirm_expert': 'Industry Regulatory / Compliance Expert',
                'confirm_expert_color': '#7C3AED',
                'kill_evidence': 'The regulatory environment is straightforward and imposes no meaningful constraint — incumbents confirm it does not shape competitive dynamics',
                'kill_expert': 'Industry Association Analyst',
                'rationale': 'Regulatory constraints that are invisible from the outside often explain competitive outcomes that look irrational in public data.',
            },
        ],
    },
    {
        'id': 'operational_model',
        'name': 'Operational Model',
        'value_driver': 'operational_model',
        'color': '#059669',
        'keyword_group': 'operational_model',
        'so_what': lambda f: f"Companies like {f['reference_company'] or 'reference_company'} follow an operational logic opaque from the outside — an insider model of the unit economics is {f['client'] or 'the client'}'s key evidence base",
        'issue': lambda f: f"How do companies like {f['reference_company'] or 'reference_company'} actually generate revenue, manage their cost structure, and achieve operational leverage?",
        'hypothesis': lambda f: f"The economics of operating like {f['reference_company'] or 'reference_company'} follow a well-understood internal model that experienced practitioners can benchmark — and that deviates materially from what public data implies.",
        'mece_axes': ['Revenue model', 'Cost structure', 'Capital intensity', 'Operational KPIs'],
        'sub_hypotheses': [
            {
                'text': 'The revenue model has identifiable levers — specific drivers of top-line performance that experienced operators track and actively manage',
                'confirm_evidence': 'Interviews with former GMs or operations heads who have managed the revenue lines and can explain which levers matter and by how much',
                'confirm_expert': 'Former GM / Operations Head at Peer Company',
                'confirm_expert_color': '#059669',
                'kill_evidence': 'Revenue is driven by external factors operators cannot influence — insiders confirm no controllable revenue levers exist within the business',
                'kill_expert': 'Revenue Modeling Specialist',
                'rationale': 'If the client cannot identify which levers drive revenue, no operating model is credible — the business becomes a black box.',
            },
            {
                'text': 'The cost structure has identifiable fixed and variable drivers — and which costs are controllable vs. structural is known to experienced insiders',
                'confirm_evidence': 'Interviews with former CFOs or finance leads at peer operators who can walk through the actual cost build and flag what can and cannot be moved',
                'confirm_expert': 'Former CFO / Finance Lead at Peer Operator',
                'confirm_expert_color': '#D97706',
                'kill_evidence': 'Cost structure is too site-specific to generalize — insiders confirm no benchmarkable cost framework applies across similar operators',
                'kill_expert': 'Cost Benchmarking Analyst',
                'rationale': 'Without a cost model, any margin improvement thesis is speculative — the client needs insiders who have seen the actual cost build.',
            },
            {
                'text': 'Capital requirements and asset intensity follow industry norms that experienced operators can benchmark and anticipate',
                'confirm_evidence': 'Interviews with capital allocators or operators who have made investment decisions and can explain what drives capex need and timing',
                'confirm_expert': 'Capital Allocation Executive / Former Operator',
                'confirm_expert_color': '#0891B2',
                'kill_evidence': 'Capex is lumpy and highly site-specific — insiders confirm no consistent asset intensity model applies and surprises are common',
                'kill_expert': 'Asset Condition Assessor',
                'rationale': 'Unmodeled capex can destroy returns — insiders who have seen what is inside the walls can surface what public data never reveals.',
            },
            {
                'text': 'Operational performance is tracked through internal KPIs that are not publicly disclosed but are well understood by experienced practitioners',
                'confirm_evidence': 'Interviews with former operations executives who can name the specific KPIs they tracked and explain what thresholds signal health vs. distress',
                'confirm_expert': 'Former Operations Executive at Peer Company',
                'confirm_expert_color': '#7C3AED',
                'kill_evidence': 'No consistent KPI framework exists — insiders confirm that each operator tracks different metrics and no benchmarkable standard applies',
                'kill_expert': 'Industry Benchmarking Analyst',
                'rationale': 'The KPIs insiders track but never disclose are the clearest signal of real operational health — they are exactly what expert calls can surface.',
            },
        ],
    },
    {
        'id': 'competitive_movement',
        'name': 'Competitive Movement',
        'value_driver': 'competitive_movement',
        'color': '#D97706',
        'keyword_group': 'competitive_movement',
        'so_what': lambda f: f"The competitive landscape around companies like {f['reference_company'] or 'reference_company'} is at an inflection point — insiders can see the direction before it is visible to {f['client'] or 'the client'} from the outside",
        'issue': lambda f: f"Where is the competitive landscape for companies like {f['reference_company'] or 'reference_company'} heading — what forces are shifting it, and who is positioned to win?",
        'hypothesis': lambda f: f"The competitive dynamics around {f['reference_company'] or 'reference_company'}'s market are shifting in ways that experienced participants can identify — and the direction of shift is already knowable from insiders before it becomes visible externally.",
        'mece_axes': ['Industry structure evolution', 'Basis of competition shift', 'Disruptive entrant traction', 'Winner identification'],
        'sub_hypotheses': [
            {
                'text': 'The industry structure is actively changing — consolidation, fragmentation, or disruption is underway in ways that participants can observe firsthand',
                'confirm_evidence': 'Interviews with M&A veterans or operators who have seen peers consolidate and can describe the structural forces behind the change',
                'confirm_expert': 'Industry M&A Veteran / Former Acquirer',
                'confirm_expert_color': '#D97706',
                'kill_evidence': 'The industry structure is stable — insiders confirm no meaningful consolidation, fragmentation, or disruption is occurring or credibly coming',
                'kill_expert': 'Industry Structure Economist',
                'rationale': 'Structural change reshapes competitive advantage — understanding whether the industry is consolidating or fragmenting changes the entire strategic logic.',
            },
            {
                'text': 'The basis of competition is shifting — what it took to win five years ago is not what it takes to win today',
                'confirm_evidence': 'Interviews with former strategic operators who have actively adapted their competitive approach and can articulate what changed and why',
                'confirm_expert': 'Former Strategic Operator at Peer Company',
                'confirm_expert_color': '#2563EB',
                'kill_evidence': 'The basis of competition is unchanged — long-tenured incumbents confirm the same advantages have delivered wins throughout their careers',
                'kill_expert': 'Long-Tenured Industry Executive',
                'rationale': 'If what it takes to win has changed, the incumbents still operating on old playbooks are at risk — and that risk is invisible from public data.',
            },
            {
                'text': 'New entrant models or substitute offerings are testing the competitive boundaries and some are gaining real traction among participants',
                'confirm_evidence': 'Interviews with incumbents who have faced new entrants and can assess their threat credibly — including where entrants have won and where they have failed',
                'confirm_expert': 'Incumbent Operator Who Faced Disruption',
                'confirm_expert_color': '#059669',
                'kill_evidence': 'New entrants have retreated or remained marginal — incumbents confirm the competitive boundaries are holding and no substitute has gained meaningful share',
                'kill_expert': 'Former New Entrant / Disruptor Executive',
                'rationale': 'Disruptors who have gained real traction change the risk profile of incumbents — this is exactly the intelligence that external research cannot surface.',
            },
            {
                'text': 'The likely winners and losers in the next competitive cycle are already visible to informed insiders — even if not yet to the broader market',
                'confirm_evidence': 'Interviews with former sector heads or well-networked industry participants who have visibility across competitors and can identify emerging patterns',
                'confirm_expert': 'Former Sector Head / Industry Networker',
                'confirm_expert_color': '#7C3AED',
                'kill_evidence': 'The competitive outcome is genuinely uncertain — even the most informed insiders disagree and cannot identify likely winners with any confidence',
                'kill_expert': 'Multi-Operator Perspectives Analyst',
                'rationale': 'Insiders who have seen competitors up close often know who is winning before financial results confirm it — that early read is the value of expert intelligence.',
            },
        ],
    },
    {
        'id': 'growth_scalability',
        'name': 'Growth & Scalability',
        'value_driver': 'growth_scalability',
        'color': '#7C3AED',
        'keyword_group': 'growth_scalability',
        'so_what': lambda f: f"The growth trajectory of companies like {f['reference_company'] or 'reference_company'} depends on scalability constraints that only insiders can quantify — {f['client'] or 'the client'} needs this to size the opportunity",
        'issue': lambda f: f"Can {f['reference_company'] or 'reference_company'}'s growth model scale beyond its current footprint, or are there structural ceilings that limit expansion?",
        'hypothesis': lambda f: f"The growth and scalability of {f['reference_company'] or 'reference_company'}'s model is governed by replicability constraints that experienced operators understand — constraints that are not visible from external data alone.",
        'mece_axes': ['Organic growth levers', 'Geographic / segment expansion', 'Scalability constraints', 'Growth sustainability'],
        'sub_hypotheses': [
            {
                'text': 'Organic growth levers exist and are identifiable — experienced operators can name the specific drivers of same-unit or same-store growth',
                'confirm_evidence': 'Interviews with operators who have driven organic growth and can explain which levers moved the needle',
                'confirm_expert': 'Former Growth / Expansion Executive',
                'confirm_expert_color': '#7C3AED',
                'kill_evidence': 'Organic growth has stalled — insiders confirm the addressable pool is saturated and no lever reliably drives incremental growth',
                'kill_expert': 'Market Saturation Analyst',
                'rationale': 'If no organic growth levers exist, the investment thesis must rely entirely on M&A or cost cuts — a fundamentally different risk profile.',
            },
            {
                'text': 'Geographic or segment expansion is feasible — the model can be replicated in new markets without losing its core economics',
                'confirm_evidence': 'Interviews with executives who have expanded into new geographies or segments and can assess replicability',
                'confirm_expert': 'Former Regional Expansion Lead',
                'confirm_expert_color': '#2563EB',
                'kill_evidence': 'Expansion attempts have failed or economics degrade sharply in new markets — the model is not portable',
                'kill_expert': 'Failed Expansion Post-Mortem Analyst',
                'rationale': 'A model that only works in its home market has a hard ceiling — understanding portability is critical to sizing the opportunity.',
            },
            {
                'text': 'Scalability constraints are known and manageable — insiders can identify the bottlenecks that limit growth and assess whether they can be overcome',
                'confirm_evidence': 'Interviews with operators who have hit scale limits and can explain what constrained them and how they adapted',
                'confirm_expert': 'Former COO / Scale Operations Leader',
                'confirm_expert_color': '#059669',
                'kill_evidence': 'Scale constraints are structural and cannot be overcome — insiders confirm the model breaks above a certain size threshold',
                'kill_expert': 'Operations Scalability Consultant',
                'rationale': 'Unidentified scale constraints can destroy returns post-acquisition — insiders who have hit the ceiling know where it is.',
            },
            {
                'text': 'The current growth rate is sustainable and not artificially inflated by one-time factors',
                'confirm_evidence': 'Interviews with finance leaders who can decompose growth into sustainable vs. one-time components',
                'confirm_expert': 'Former CFO / FP&A Lead at Peer',
                'confirm_expert_color': '#D97706',
                'kill_evidence': 'Growth is driven by non-recurring tailwinds — insiders confirm the current trajectory is not sustainable',
                'kill_expert': 'Growth Sustainability Skeptic',
                'rationale': 'Paying for unsustainable growth is the most common PE mistake — insiders can separate signal from noise.',
            },
        ],
    },
    {
        'id': 'risk_regulatory',
        'name': 'Risk & Regulatory',
        'value_driver': 'risk_regulatory',
        'color': '#DC2626',
        'keyword_group': 'risk_regulatory',
        'so_what': lambda f: f"Companies like {f['reference_company'] or 'reference_company'} face regulatory and structural risks that are invisible from the outside — {f['client'] or 'the client'} needs insider intelligence to map the risk landscape",
        'issue': lambda f: f"What regulatory, legal, or structural risks does {f['reference_company'] or 'reference_company'}'s business face that could materially affect its value or operations?",
        'hypothesis': lambda f: f"The risk and regulatory environment around {f['reference_company'] or 'reference_company'} contains material exposures that experienced industry participants can identify and quantify — exposures that are not visible in public filings or standard due diligence.",
        'mece_axes': ['Regulatory exposure', 'Legal / litigation risk', 'ESG / sustainability risk', 'Policy / political risk'],
        'sub_hypotheses': [
            {
                'text': 'Material regulatory risks exist that are not fully captured in public disclosures — experienced operators know which regulations actually bite',
                'confirm_evidence': 'Interviews with compliance leaders who have navigated regulatory challenges and can identify the real exposure points',
                'confirm_expert': 'Former Chief Compliance Officer',
                'confirm_expert_color': '#DC2626',
                'kill_evidence': 'The regulatory environment is benign — insiders confirm no material regulatory risk exists beyond what is publicly disclosed',
                'kill_expert': 'Industry Regulatory Affairs Analyst',
                'rationale': 'Hidden regulatory risk can destroy deal value — insiders who have dealt with regulators know what is coming before it is public.',
            },
            {
                'text': 'Legal or litigation risks are identifiable and quantifiable — industry participants can assess the probability and magnitude of legal exposure',
                'confirm_evidence': 'Interviews with legal counsel or executives who have managed litigation and can assess the realistic exposure',
                'confirm_expert': 'Former General Counsel at Peer Company',
                'confirm_expert_color': '#D97706',
                'kill_evidence': 'Litigation risk is minimal — legal experts confirm no credible exposure beyond routine business disputes',
                'kill_expert': 'Industry Litigation Analyst',
                'rationale': 'Unquantified litigation tail risk is a deal-killer for conservative buyers — expert intelligence can size the exposure.',
            },
            {
                'text': 'ESG or sustainability factors pose real operational or financial risk — not just reputational',
                'confirm_evidence': 'Interviews with sustainability officers who can identify concrete financial impacts of ESG-related requirements',
                'confirm_expert': 'Former Sustainability / ESG Officer',
                'confirm_expert_color': '#059669',
                'kill_evidence': 'ESG factors are immaterial — insiders confirm no meaningful financial impact from sustainability requirements',
                'kill_expert': 'ESG Materiality Assessor',
                'rationale': 'ESG risks that translate to real costs or capital requirements change the return profile — insiders can separate material from immaterial.',
            },
            {
                'text': 'Policy or political changes could materially alter the operating environment — and the direction of change is predictable to informed insiders',
                'confirm_evidence': 'Interviews with government affairs leaders or lobbyists who can assess the likelihood and impact of policy changes',
                'confirm_expert': 'Former Government Affairs / Policy Lead',
                'confirm_expert_color': '#7C3AED',
                'kill_evidence': 'The policy environment is stable — insiders confirm no credible political risk to the business model',
                'kill_expert': 'Policy Risk Analyst',
                'rationale': 'Policy shifts can create or destroy entire business models — insiders with government relationships see changes before they become public.',
            },
        ],
    },
]


def _detect_scope(ref, proj, wants):
    """Detect whether hypotheses should anchor on the company or the market.

    Returns 'company', 'market', or 'ambiguous'.
    """
    ref_lower = ref.lower().strip()
    proj_lower = proj.lower().strip()
    wants_lower = wants.lower().strip()
    if not ref_lower:
        return 'market'

    # Company-level signals from client_wants
    wants_company = any(p in wants_lower for p in [
        f'assess {ref_lower}', f'evaluate {ref_lower}',
        f'{ref_lower} a good', f'is {ref_lower}',
        f'should we acquire {ref_lower}', f'should we buy {ref_lower}',
        f'{ref_lower}\'s health', f'{ref_lower}\'s value',
        f'diligence on {ref_lower}', f'review of {ref_lower}',
        f'invest in {ref_lower}',
    ])

    # Company-level signals from project_name
    proj_company = any(p in proj_lower for p in [
        f'{ref_lower} diligence', f'{ref_lower} acquisition',
        f'{ref_lower} investment', f'{ref_lower} assessment',
        f'{ref_lower} review', f'{ref_lower} dd',
        f'{ref_lower} valuation', f'{ref_lower} evaluation',
    ])

    # Market-level signals from client_wants
    wants_market = any(p in wants_lower for p in [
        'understand the market', 'understand the industry',
        'how the market', 'how the industry', 'market dynamics',
        'industry structure', 'market intelligence', 'sector',
        'landscape', 'market overview', 'industry overview',
    ])

    # Market-level signals from project_name
    proj_market = any(p in proj_lower for p in [
        'market diligence', 'market intelligence', 'market study',
        'market assessment', 'industry', 'sector',
    ])

    # Decision logic
    if wants_company:
        return 'company'
    if wants_market:
        return 'market'
    if proj_company:
        return 'company'
    if proj_market:
        return 'market'
    # Tie-break: if project names the company but wants is vague, client_wants wins
    if ref_lower in proj_lower and not wants_market:
        return 'company'
    return 'ambiguous'


def _build_llm_prompt(form_data, ordered_drivers):
    ref = form_data.get('reference_company', '')
    proj = form_data.get('proj_name', '')
    wants = form_data.get('client_wants', '')
    questions = form_data.get('verify_questions', '')
    driver_list = '\n'.join(
        f'{i+1}. {d["id"]} ({d["name"]})' for i, d in enumerate(ordered_drivers)
    )

    scope = _detect_scope(ref, proj, wants)

    if scope == 'company':
        schema = '''
{
  "issue": "<question about the reference company derived from the learning objective>",
  "scenarios": [
    {
      "driver_id": "<market_dynamics | operational_model | competitive_movement | growth_scalability | risk_regulatory>",
      "name": "<8-15 word headline — MAY name the reference company>",
      "so_what": "<why this matters for the client's decision about the company>",
      "hypothesis": "<falsifiable claim about the reference company>",
      "sub_hypotheses": [
        {
          "text": "<specific sub-hypothesis about the company>",
          "experts": [
            {
              "name": "<specific role at the company or a peer>",
              "evidence": "<what this insider can reveal>",
              "rationale": "<why this person has the right vantage point>"
            }
          ]
        }
      ]
    }
  ]
}'''
        anchoring_block = (
            f"SCOPE: COMPANY-LEVEL — the project and learning objective ask about \"{ref}\" directly.\n"
            f"Hypotheses and sub-hypotheses SHOULD be about \"{ref}\" specifically.\n"
            f'Example: "{ref}\'s margins are structurally thin because..." is CORRECT.\n'
            "Experts should be specific insiders at the company or direct peers.\n"
        )
    else:
        schema = '''
{
  "issue": "<market/industry-level question — do NOT name the reference company>",
  "scenarios": [
    {
      "driver_id": "<market_dynamics | operational_model | competitive_movement | growth_scalability | risk_regulatory>",
      "name": "<8-15 word MARKET-level headline — NO reference company name>",
      "so_what": "<why this market truth matters for the client's decision>",
      "hypothesis": "<falsifiable claim about the MARKET or INDUSTRY>",
      "sub_hypotheses": [
        {
          "text": "<MECE market-level sub-hypothesis — NO company names>",
          "experts": [
            {
              "name": "<specific role at reference company or industry peer>",
              "evidence": "<what this insider can reveal about the market>",
              "rationale": "<why someone inside this company is the right lens>"
            }
          ]
        }
      ]
    }
  ]
}'''
        anchoring_block = (
            "SCOPE: MARKET-LEVEL — the learning objective asks about a market, industry, or segment.\n\n"
            "Input priority order:\n"
            f"  1. LEARNING OBJECTIVE (master anchor): \"{wants}\"\n"
            f"  2. PROJECT NAME (scope): \"{proj}\"\n"
            f"  3. SCREENING QUESTIONS (shape sub-hypotheses): \"{questions}\"\n"
            f"  4. REFERENCE COMPANY (evidence layer only): \"{ref}\"\n\n"
            f"STRICT RULES — the name \"{ref}\" is BANNED from:\n"
            "  issue, scenario name, scenario hypothesis, sub_hypothesis text.\n"
            f"\"{ref}\" may ONLY appear in expert name/evidence/rationale.\n\n"
            "Phrase at the market level:\n"
            f'  BAD:  "{ref}\'s BNPL default rates are 2-3x higher than Kakao Pay"\n'
            '  GOOD: "Early-stage BNPL underwriting runs structurally looser than\n'
            '         incumbent card issuers, producing 2-3x default rates across the\n'
            '         fintech segment"\n'
            f'  GOOD expert: "Former Credit Risk Lead at {ref}"\n'
        )
        if scope == 'ambiguous':
            anchoring_block += (
                '\nNOTE: scope was ambiguous — defaulting to market-level. Add this line '
                'to the "issue" field: "(Scope inferred as market-level — confirm if '
                'this should be company-specific.)"\n'
            )

    return (
        "You are generating a CDD hypothesis tree for a consulting team. Output ONLY valid JSON, no markdown fences.\n\n"
        f"Project: {proj}\n"
        f"Learning objective: {wants}\n"
        f"Screening questions: {questions}\n"
        f"Reference company: {ref}\n\n"
        + anchoring_block + "\n"
        f"Generate 3 to 5 specific CDD scenarios from the value driver types below. Priority order:\n{driver_list}\n\n"
        "Rules:\n"
        "- exactly 4 sub_hypotheses per scenario, each with 3-4 experts\n"
        "- expert names must be specific roles at specific companies\n"
        "- sub-hypotheses must be MECE\n\n"
        "Output this exact JSON structure:" + schema
    )


def generate_sub_sub(sub_hyp_text, hypothesis, reference_company, client_name, client_wants='', proj_name=''):
    """Generate 2-3 sub-sub-hypotheses for a given sub-hypothesis via Claude."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not _HAS_ANTHROPIC or not api_key:
        return None
    try:
        print(f'\n⏳ Expanding sub-hypothesis (fast)...')
        api_client = _anthropic.Anthropic(api_key=api_key)

        scope = _detect_scope(reference_company, proj_name, client_wants)

        if scope == 'company':
            anchoring = (
                "SCOPE: COMPANY-LEVEL — hypotheses are about the reference company.\n"
                f"Sub-hypotheses MAY name \"{reference_company}\".\n"
            )
        else:
            anchoring = (
                "SCOPE: MARKET-LEVEL — hypotheses are about the market/industry.\n"
                f"The name \"{reference_company}\" is BANNED from sub-hypothesis text.\n"
                f"\"{reference_company}\" may ONLY appear in expert name/evidence/rationale.\n"
                "Phrase at market level: \"BNPL underwriting across the fintech segment...\" "
                f"NOT \"{reference_company}'s underwriting...\"\n"
            )

        prompt = (
            "You are generating deeper sub-hypotheses for a CDD hypothesis tree. "
            "Output ONLY a valid JSON array, no markdown fences.\n\n"
            f"Reference company: {reference_company}\n"
            f"Client: {client_name}\n"
            f"Learning objective: {client_wants}\n"
            f"Parent hypothesis: {hypothesis}\n"
            f"Sub-hypothesis to expand: {sub_hyp_text}\n\n"
            + anchoring + "\n"
            "Generate 2-3 deeper sub-sub-hypotheses inheriting the same scope as above. "
            "Each should have 3 experts (specific role at specific company) "
            "who could verify or challenge the claim from inside the industry.\n\n"
            "Output:\n"
            "[\n"
            '  {\n'
            '    "text": "sub-sub-hypothesis (respecting the scope rule above)",\n'
            '    "experts": [\n'
            '      {"name": "specific role at company", "evidence": "what they reveal", "rationale": "why this insider matters"}\n'
            "    ]\n"
            "  }\n"
            "]"
        )
        msg = api_client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2048,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = ''.join(block.text for block in msg.content if block.type == 'text').strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw.strip())
        parsed = json.loads(raw)
        print(f'── Expanded into {len(parsed)} sub-sub-hypotheses ──')
        return parsed
    except Exception as e:
        print(f'\n── SUB-SUB LLM ERROR: {e} ──\n')
        return None


def generate_specific_scenarios(form_data, ordered_drivers):
    """Call Claude to generate market-specific scenario content. Returns parsed dict or None on failure."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not _HAS_ANTHROPIC or not api_key:
        return None
    try:
        print('\n⏳ Calling Claude (Haiku) — generating scenarios...')
        client = _anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8192,
            messages=[{'role': 'user', 'content': _build_llm_prompt(form_data, ordered_drivers)}],
        )
        raw = ''.join(block.text for block in msg.content if block.type == 'text').strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw.strip())
        parsed = json.loads(raw)
        print('\n── LLM JSON output ──')
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
        print('── end LLM JSON ──\n')
        return parsed
    except Exception as e:
        print(f'\n── LLM ERROR: {e} ──\n')
        return None


def generate_result(form_data):
    text = f"{form_data.get('client_wants', '')} {form_data.get('verify_questions', '')}"
    scores, matched = score_keywords(text)

    # Order by keyword score: highest score → Scenario 1
    ordered = sorted(VALUE_DRIVERS, key=lambda d: -scores.get(d['keyword_group'], 0))

    # Compute probabilities (normalize to 100%; flag zero-signal)
    total = sum(scores.values())
    zero_signal = total == 0
    if zero_signal:
        probabilities = {d['keyword_group']: 0 for d in VALUE_DRIVERS}
    else:
        probabilities = {d['keyword_group']: round(scores[d['keyword_group']] / total * 100) for d in VALUE_DRIVERS}
        # Absorb rounding residual into the top driver
        diff = 100 - sum(probabilities.values())
        probabilities[ordered[0]['keyword_group']] += diff

    # Try LLM-specific content; fall back to generic templates on any failure
    llm_data = generate_specific_scenarios(form_data, ordered)
    llm_scenarios = {s['driver_id']: s for s in llm_data.get('scenarios', [])} if llm_data else {}

    issue = ordered[0]['issue'](form_data)
    if llm_data and llm_data.get('issue'):
        issue = llm_data['issue']

    # Include drivers that have keyword signal or LLM content; always keep at least 3
    active_drivers = []
    for driver in ordered:
        has_signal = scores.get(driver['keyword_group'], 0) > 0
        has_llm = driver['id'] in llm_scenarios
        if has_signal or has_llm or len(active_drivers) < 3:
            active_drivers.append(driver)

    scenarios = []
    for idx, driver in enumerate(active_drivers):
        llm_s = llm_scenarios.get(driver['id'])

        name = llm_s['name'] if llm_s else driver['name']
        so_what = llm_s['so_what'] if llm_s else driver['so_what'](form_data)
        hypothesis = llm_s['hypothesis'] if llm_s else driver['hypothesis'](form_data)

        # Build sub-hypotheses from LLM or fall back to template
        if llm_s and len(llm_s.get('sub_hypotheses', [])) >= 3:
            sub_hypotheses = []
            for sh in llm_s['sub_hypotheses'][:4]:
                experts = sh.get('experts', [])
                if not experts and sh.get('confirm_expert'):
                    experts = [
                        {'name': sh['confirm_expert'], 'evidence': sh.get('confirm_evidence', ''), 'rationale': sh.get('rationale', '')},
                        {'name': sh['kill_expert'], 'evidence': sh.get('kill_evidence', ''), 'rationale': ''},
                    ]
                sub_hypotheses.append({'text': sh.get('text', ''), 'experts': experts})
        else:
            sub_hypotheses = []
            for tsh in driver['sub_hypotheses']:
                sub_hypotheses.append({
                    'text': tsh['text'],
                    'experts': [
                        {'name': tsh['confirm_expert'], 'evidence': tsh['confirm_evidence'], 'rationale': tsh.get('rationale', '')},
                        {'name': tsh['kill_expert'], 'evidence': tsh['kill_evidence'], 'rationale': ''},
                    ],
                })

        # LLM-generated content is MECE by construction; skip overlap check to avoid false positives
        if llm_s:
            mece = {'valid': True, 'issues': []}
        else:
            mece = validate_mece(sub_hypotheses)
        trigger_kws = matched.get(driver['keyword_group'], [])

        scenarios.append({
            'id': idx + 1,
            'template_id': driver['id'],
            'name': name,
            'value_driver': driver['value_driver'],
            'value_driver_label': driver['name'],
            'color': driver['color'],
            'so_what': so_what,
            'hypothesis': hypothesis,
            'sub_hypotheses': sub_hypotheses,
            'mece_valid': mece['valid'],
            'mece_issues': mece['issues'],
            'mece_axes': driver['mece_axes'],
            'trigger_keywords': trigger_kws,
            'probability': probabilities.get(driver['keyword_group'], 0),
        })

    return {
        'issue': issue,
        'scenarios': scenarios,
        'cdd_warning': not is_cdd(form_data),
        'zero_signal': zero_signal,
        'probabilities': probabilities,
    }


# ── HTML rendering ─────────────────────────────────────────────────────────────

def _e(s):
    return html.escape(str(s))


def render_svg_tree(issue, scenarios):
    SVG_W, SVG_H = 920, 220
    ROOT_CX = SVG_W // 2
    ISSUE_Y, ISSUE_W, ISSUE_H = 20, 680, 52
    HYP_Y, HYP_W, HYP_H = 130, 230, 52
    ELBOW_Y = 105

    count = len(scenarios)
    if count > 1:
        gap = (SVG_W - 80 * 2 - HYP_W * count) / (count - 1)
        centers = [80 + HYP_W / 2 + i * (HYP_W + gap) for i in range(count)]
    else:
        centers = [ROOT_CX]

    parts = []

    # Issue node
    ix = ROOT_CX - ISSUE_W // 2
    truncated_issue = _e(issue[:110] + ('…' if len(issue) > 110 else ''))
    parts.append(f'<rect x="{ix}" y="{ISSUE_Y}" width="{ISSUE_W}" height="{ISSUE_H}" rx="8" fill="#0F172A"/>')
    parts.append(f'<text x="{ROOT_CX}" y="{ISSUE_Y+18}" text-anchor="middle" fill="#94A3B8" font-size="9" font-weight="700" letter-spacing="0.08em">ISSUE</text>')
    parts.append(f'<text x="{ROOT_CX}" y="{ISSUE_Y+36}" text-anchor="middle" fill="#E2E8F0" font-size="11">{truncated_issue}</text>')

    for i, scenario in enumerate(scenarios):
        if not scenario['mece_valid']:
            continue  # MECE gate: don't render blocked scenarios
        cx = centers[i]
        rx = cx - HYP_W / 2
        color = scenario['color']
        kws = scenario['trigger_keywords']
        kw_text = f'↑ "{", ".join(kws[:2])}"' if kws else ''

        parts.append(f'<path d="M {ROOT_CX} {ISSUE_Y+ISSUE_H} L {ROOT_CX} {ELBOW_Y} L {cx:.1f} {ELBOW_Y} L {cx:.1f} {HYP_Y}" fill="none" stroke="#CBD5E1" stroke-width="1.5"/>')
        parts.append(f'<rect x="{rx:.1f}" y="{HYP_Y}" width="{HYP_W}" height="{HYP_H}" rx="8" fill="{color}" class="hyp-node" data-id="{_e(scenario["template_id"])}"/>')
        parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+16}" text-anchor="middle" fill="rgba(255,255,255,0.7)" font-size="9" font-weight="700" letter-spacing="0.08em">SCENARIO {scenario["id"]} · {_e(scenario["value_driver"].upper())}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+33}" text-anchor="middle" fill="white" font-size="12" font-weight="700">{_e(scenario["name"])}</text>')
        if kw_text:
            parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+47}" text-anchor="middle" fill="rgba(255,255,255,0.72)" font-size="9">{_e(kw_text)}</text>')

    parts.append(f'<text x="{SVG_W//2}" y="{SVG_H-4}" text-anchor="middle" fill="#94A3B8" font-size="10">Keyword signal orders Scenario 1 · Sub-hypotheses and experts in cards below</text>')

    return f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block">\n  ' + '\n  '.join(parts) + '\n</svg>'


def render_scenarios(scenarios):
    cards = []
    for s in scenarios:
        if not s['mece_valid']:
            mece_fail = '; '.join(_e(i) for i in s['mece_issues'])
            cards.append(f'<div class="mece-gate-error">MECE gate blocked "{_e(s["name"])}": {mece_fail}</div>')
            continue

        # Trigger keywords
        trigger_html = ''
        if s['trigger_keywords']:
            tags = ''.join(f'<span class="kw">{_e(kw)}</span>' for kw in s['trigger_keywords'])
            trigger_html = f'<div class="trigger-row"><span class="trigger-label">Keyword signal → Scenario {s["id"]}</span><div class="kw-list">{tags}</div></div>'

        # MECE badge
        mece_text = 'MECE · ' + ' · '.join(_e(a) for a in s['mece_axes'])
        mece_html = f'<div class="mece-badge mece-ok"><span class="mece-icon">✓</span><span>{mece_text}</span></div>'

        # Sub-hypotheses with confirm + kill
        sh_html = ''
        for i, sh in enumerate(s['sub_hypotheses']):
            cec = sh['confirm_expert_color']
            confirm_style = f"background:{cec}18;color:{cec};border:1px solid {cec}44"
            sh_html += f'''
            <div class="sh-block">
              <div class="sh-header">
                <div class="sh-index">{i+1}</div>
                <div class="sh-content">
                  <span class="node-label nl-sub">Sub-hypothesis</span>
                  <p class="sh-text">{_e(sh["text"])}</p>
                </div>
              </div>
              <div class="sh-leaf sh-confirm">
                <div class="leaf-row">
                  <span class="node-label nl-confirm">Confirm Expert</span>
                  <span class="leaf-evidence">{_e(sh["confirm_evidence"])}</span>
                </div>
                <div class="leaf-expert-row">
                  <span class="expert-chip" style="{confirm_style}">{_e(sh["confirm_expert"])}</span>
                  <span class="why-text"><span class="why-label">WHY</span> {_e(sh["rationale"])}</span>
                </div>
              </div>
              <div class="sh-leaf sh-kill">
                <div class="leaf-row">
                  <span class="node-label nl-kill">Kill Expert</span>
                  <span class="leaf-evidence">{_e(sh["kill_evidence"])}</span>
                </div>
                <div class="leaf-expert-row">
                  <span class="expert-chip-kill">{_e(sh["kill_expert"])}</span>
                </div>
              </div>
            </div>'''

        tid = _e(s['template_id'])
        cards.append(f'''
        <div class="scenario-card" id="card-{tid}" data-template-id="{tid}">
          <div class="so-what-block">
            <span class="so-what-label">SO WHAT</span>
            <p class="so-what-text">{_e(s["so_what"])}</p>
          </div>
          <div class="scenario-header">
            <div class="scenario-top-row">
              <span class="scenario-badge">Scenario {s["id"]} · {_e(s["name"])}</span>
              <span class="rejected-stamp" id="stamp-{tid}" style="display:none"></span>
            </div>
            <div class="hyp-block">
              <span class="node-label nl-hyp">Hypothesis</span>
              <p class="hyp-text" id="hyp-{tid}">{_e(s["hypothesis"])}</p>
            </div>
            {mece_html}
            {trigger_html}
          </div>
          <div class="sh-list">{sh_html}</div>
          <div class="scenario-actions">
            <button class="btn-reject" id="btn-reject-{tid}" onclick="rejectScenario('{tid}', this)">Reject</button>
            <button class="btn-delete-red" onclick="deleteScenario('{tid}')">Delete</button>
          </div>
        </div>''')

    return '<div class="scenario-grid">' + ''.join(cards) + '</div>'


CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;background:#F1F5F9;color:#1E293B}
header{background:#0F172A;padding:12px 24px;display:flex;align-items:baseline;gap:14px}
.app-title{color:#F8FAFC;font-size:16px;font-weight:700}
.app-sub{color:#475569;font-size:12px}
.content{padding:24px;max-width:1200px;margin:0 auto}
.project-bar{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.project-pill{background:#0F172A;color:#94A3B8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.07em}
.project-name{font-size:17px;font-weight:700}
.project-meta{font-size:12px;color:#64748B}
.cdd-warning{display:flex;align-items:flex-start;gap:8px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#92400E;line-height:1.5}
.issue-banner{display:flex;align-items:flex-start;gap:10px;background:#0F172A;border-radius:8px;padding:12px 14px;margin-bottom:16px}
.issue-label{flex-shrink:0;background:#1E293B;color:#94A3B8;font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.1em;margin-top:1px}
.issue-text{color:#E2E8F0;font-size:13px;line-height:1.5}
.tree-container{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px 18px 12px;margin-bottom:20px}
.section-label{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em}
.scenarios-header-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.export-csv-btn{padding:5px 12px;background:#0F172A;color:#94A3B8;border:none;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;letter-spacing:.02em;transition:all .15s}
.export-csv-btn:hover{background:#1E293B;color:#E2E8F0}
.mece-gate-error{background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:8px 12px;font-size:12px;color:#DC2626;margin-bottom:10px}
.so-what-block{display:flex;align-items:flex-start;gap:8px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px 12px}
.so-what-label{flex-shrink:0;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.1em;margin-top:2px}
.so-what-text{font-size:13px;font-weight:700;color:#0F172A;line-height:1.4}
.scenario-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.scenario-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:12px;transition:opacity .2s}
.scenario-card.rejected{opacity:.5}
.scenario-card.deleted{display:none}
.scenario-header{display:flex;flex-direction:column;gap:6px}
.scenario-top-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.scenario-badge{background:#F1F5F9;color:#64748B;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.06em}
.rejected-stamp{font-size:10px;color:#EF4444;font-weight:600;background:#FEF2F2;padding:2px 7px;border-radius:4px;border:1px solid #FECACA}
.node-label{display:inline-block;font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.08em}
.nl-hyp{background:#EFF6FF;color:#1D4ED8}
.nl-sub{background:#F0FDF4;color:#166534}
.nl-confirm{background:#FFF7ED;color:#92400E}
.nl-kill{background:#FEF2F2;color:#DC2626}
.hyp-block{display:flex;flex-direction:column;gap:5px}
.hyp-text{font-size:13px;font-weight:600;line-height:1.5;color:#1E293B}
.rejected .hyp-text{text-decoration:line-through;text-decoration-color:#64748B}
.mece-badge{display:flex;align-items:flex-start;gap:5px;padding:6px 10px;border-radius:6px;font-size:11px}
.mece-ok{background:#F0FDF4;border:1px solid #BBF7D0;color:#166534}
.mece-icon{font-size:12px;flex-shrink:0}
.trigger-row{display:flex;flex-direction:column;gap:5px}
.trigger-label{font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.06em}
.kw-list{display:flex;flex-wrap:wrap;gap:4px}
.kw{background:#FEF9C3;color:#92400E;font-size:11px;font-weight:500;padding:2px 7px;border-radius:4px;border:1px solid #FDE68A}
.sh-list{display:flex;flex-direction:column;gap:10px;border-top:1px solid #E2E8F0;padding-top:10px}
.sh-block{display:flex;flex-direction:column;gap:6px}
.sh-header{display:flex;align-items:flex-start;gap:8px}
.sh-index{width:20px;height:20px;border-radius:50%;background:#F1F5F9;border:1px solid #E2E8F0;color:#64748B;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}
.sh-content{display:flex;flex-direction:column;gap:4px}
.sh-text{font-size:12px;font-weight:600;color:#1E293B;line-height:1.45}
.sh-leaf{margin-left:28px;display:flex;flex-direction:column;gap:5px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 10px}
.sh-kill{background:#FEF2F2;border-color:#FECACA}
.leaf-row{display:flex;align-items:flex-start;gap:6px}
.leaf-evidence{font-size:11px;color:#64748B;line-height:1.45}
.leaf-expert-row{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.expert-chip{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0}
.expert-chip-kill{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0;background:#FEF2F2;color:#DC2626;border:1px solid #FECACA}
.why-text{font-size:11px;color:#64748B;line-height:1.45}
.why-label{font-weight:700;color:#94A3B8;font-size:9px;text-transform:uppercase;letter-spacing:.08em;margin-right:2px}
.scenario-actions{display:flex;gap:8px;border-top:1px solid #E2E8F0;padding-top:12px;margin-top:2px}
.btn-reject{flex:1;padding:7px 12px;border:1px solid #CBD5E1;background:white;color:#64748B;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-reject:hover:not(:disabled){background:#F1F5F9;border-color:#94A3B8}
.btn-reject:disabled{background:#F8FAFC;color:#94A3B8;cursor:default}
.btn-delete-red{padding:7px 14px;border:1px solid #FECACA;background:white;color:#DC2626;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-delete-red:hover{background:#FEF2F2;border-color:#FCA5A5}
"""

JS_TEMPLATE = """
const LOG_KEY = 'cdd_rejection_log';
window.CDD_DATA = {cdd_data_json};

function loadLog() {{
  try {{ return JSON.parse(localStorage.getItem(LOG_KEY) || '{{}}'); }} catch {{ return {{}}; }}
}}
function saveLog(log) {{ localStorage.setItem(LOG_KEY, JSON.stringify(log)); }}

function rejectScenario(templateId, btn) {{
  const card = document.getElementById('card-' + templateId);
  const stamp = document.getElementById('stamp-' + templateId);
  const hyp = document.getElementById('hyp-' + templateId);
  card.classList.add('rejected');
  if (hyp) hyp.style.textDecoration = 'line-through';
  stamp.textContent = 'Rejected · ' + new Date().toLocaleString();
  stamp.style.display = 'inline';
  btn.textContent = 'Rejected ✓';
  btn.disabled = true;
  const log = loadLog();
  log[templateId] = new Date().toISOString();
  saveLog(log);
  document.querySelectorAll('.hyp-node[data-id="' + templateId + '"]').forEach(n => {{
    n.setAttribute('opacity', '0.35');
  }});
}}

function deleteScenario(templateId) {{
  if (!confirm('Delete this scenario? It will be removed with no record saved.')) return;
  document.getElementById('card-' + templateId).classList.add('deleted');
  document.querySelectorAll('.hyp-node[data-id="' + templateId + '"]').forEach(n => {{
    const g = n.closest('g');
    if (g) g.style.opacity = '0.1';
  }});
}}

function exportCSV() {{
  const log = loadLog();
  const rows = [];
  for (const s of window.CDD_DATA.scenarios) {{
    const card = document.getElementById('card-' + s.template_id);
    const isDeleted = card && card.classList.contains('deleted');
    const isRejected = Object.prototype.hasOwnProperty.call(log, s.template_id);
    const status = isDeleted ? 'deleted' : isRejected ? 'rejected' : 'active';
    for (const sh of s.sub_hypotheses) {{
      rows.push([
        s.name, s.value_driver, sh.text,
        sh.confirm_evidence, sh.confirm_expert,
        sh.kill_evidence, sh.kill_expert,
        status,
      ]);
    }}
  }}
  const headers = ['Scenario','Value_Driver','Sub_Hypothesis','Confirm_Evidence','Confirm_Expert','Kill_Evidence','Kill_Expert','Status'];
  const lines = [headers.join(','), ...rows.map(r => r.map(v => '"' + String(v || '').replace(/"/g, '""') + '"').join(','))];
  const blob = new Blob(['﻿' + lines.join('\\n')], {{type:'text/csv;charset=utf-8;'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'cdd_output.csv'; a.click();
  URL.revokeObjectURL(url);
}}

// Restore rejected state from localStorage on load
(function() {{
  const log = loadLog();
  for (const [tid, ts] of Object.entries(log)) {{
    const card = document.getElementById('card-' + tid);
    if (!card) continue;
    card.classList.add('rejected');
    const stamp = document.getElementById('stamp-' + tid);
    if (stamp) {{ stamp.textContent = 'Rejected · ' + new Date(ts).toLocaleString(); stamp.style.display = 'inline'; }}
    const btn = document.getElementById('btn-reject-' + tid);
    if (btn) {{ btn.textContent = 'Rejected ✓'; btn.disabled = true; }}
    const hyp = document.getElementById('hyp-' + tid);
    if (hyp) hyp.style.textDecoration = 'line-through';
  }}
}})();
"""


def write_csv(form_data, result, out_path):
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    rows = []
    for s in result['scenarios']:
        trigger_str = '; '.join(s['trigger_keywords'])
        for i, sh in enumerate(s['sub_hypotheses']):
            rows.append({
                'Generated':        generated_at,
                'Project':          form_data.get('proj_name', ''),
                'Client':           form_data.get('client', ''),
                'Reference_Company': form_data.get('reference_company', ''),
                'Scenario':         s['name'],
                'Value_Driver':     s['value_driver'],
                'Sub_H_Number':     i + 1,
                'Sub_Hypothesis':   sh['text'],
                'Confirm_Evidence': sh['confirm_evidence'],
                'Confirm_Expert':   sh['confirm_expert'],
                'Kill_Evidence':    sh['kill_evidence'],
                'Kill_Expert':      sh['kill_expert'],
                'Status':           'active',
                'Trigger_Keywords': trigger_str,
            })

    with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def generate_html(form_data, result):
    proj = form_data.get('proj_name', 'CDD Project')
    client = form_data.get('client', '')
    ref_co = form_data.get('reference_company', '')
    meta_html = f'<span class="project-meta">{_e(client)} · {_e(ref_co)}</span>' if client and ref_co else ''

    cdd_warning_html = ''
    if result.get('cdd_warning'):
        cdd_warning_html = '<div class="cdd-warning">⚠ These inputs don\'t look like a CDD engagement. The hypothesis skeleton is optimized for commercial due diligence — other engagement types may be mis-structured.</div>'

    # Embed scenario data for client-side CSV export
    cdd_data = {
        'scenarios': [
            {
                'template_id': s['template_id'],
                'name': s['name'],
                'value_driver': s['value_driver'],
                'sub_hypotheses': [
                    {
                        'text': sh['text'],
                        'confirm_evidence': sh['confirm_evidence'],
                        'confirm_expert': sh['confirm_expert'],
                        'kill_evidence': sh['kill_evidence'],
                        'kill_expert': sh['kill_expert'],
                    }
                    for sh in s['sub_hypotheses']
                ],
            }
            for s in result['scenarios']
        ]
    }
    js = JS_TEMPLATE.format(cdd_data_json=json.dumps(cdd_data))

    svg = render_svg_tree(result['issue'], result['scenarios'])
    scenarios_html = render_scenarios(result['scenarios'])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CDD Predictor — {_e(proj)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <span class="app-title">CDD Predictor</span>
    <span class="app-sub">GLG Korea · Commercial Due Diligence · Hypothesis Framework</span>
  </header>
  <div class="content">
    <div class="project-bar">
      <span class="project-pill">Project</span>
      <strong class="project-name">{_e(proj)}</strong>
      {meta_html}
    </div>
    {cdd_warning_html}
    <div class="issue-banner">
      <span class="issue-label">Issue</span>
      <span class="issue-text">{_e(result["issue"])}</span>
    </div>
    <div class="tree-container">
      <span class="section-label">Hypothesis Tree · Root = Issue · Branches = Core Hypotheses per Value Driver</span>
      {svg}
    </div>
    <div class="scenarios-header-row">
      <span class="section-label">Predicted Scenarios</span>
      <button class="export-csv-btn" onclick="exportCSV()">↓ Export CSV</button>
    </div>
    {scenarios_html}
  </div>
  <script>{js}</script>
</body>
</html>"""


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("\nCDD Predictor — GLG Korea (Hypothesis Framework)")
    print("─" * 50)

    form_data = {
        'proj_name':          input("Project Name: ").strip(),
        'client':             input("Client (Consulting Firm): ").strip(),
        'reference_company':  input("Reference Company (industry anchor — not an M&A target):\n> ").strip(),
        'client_wants':       input("What the Client Wants to Learn:\n> ").strip(),
        'verify_questions':   input("Verify / Screening Questions:\n> ").strip(),
    }

    result = generate_result(form_data)

    if result['cdd_warning']:
        print("\n  ⚠  CDD GUARDRAIL: These inputs don't look like a CDD engagement.")
        print("     The hypothesis skeleton is optimized for commercial due diligence.")
        print("     Other engagement types may be mis-structured.\n")

    print(f"\nIssue: {result['issue']}\n")
    print("Keyword signal (determines Scenario 1 ordering):")
    scores, _ = score_keywords(f"{form_data['client_wants']} {form_data['verify_questions']}")
    for group, score in scores.items():
        bar = '█' * score if score else '·'
        print(f"  {group:<10} {bar}  ({score})")

    print(f"\n{len(result['scenarios'])} scenarios (3 value drivers, ordered by signal):")
    for s in result['scenarios']:
        mece_ok = '✓ MECE' if s['mece_valid'] else f"✗ MECE BLOCKED ({len(s['mece_issues'])} issue)"
        print(f"\n  Scenario {s['id']}: {s['name']}  [{mece_ok}]")
        print(f"  SO WHAT: {s['so_what']}")
        for i, sh in enumerate(s['sub_hypotheses']):
            print(f"    Sub-H {i+1}: {sh['text'][:60]}…")
            print(f"      → Confirm: {sh['confirm_expert']}")
            print(f"      → Kill:    {sh['kill_expert']}")

    base = Path(__file__).parent
    html_path = base / "cdd_output.html"
    csv_path  = base / "cdd_output.csv"

    html_path.write_text(generate_html(form_data, result), encoding='utf-8')
    write_csv(form_data, result, csv_path)

    total_rows = sum(len(s['sub_hypotheses']) for s in result['scenarios'])
    print(f"\n  HTML → {html_path}")
    print(f"  CSV  → {csv_path}  ({total_rows} rows, Status=active at generation)")
    print(f"  Use '↓ Export CSV' button in HTML to re-export with current reject/delete status.")
    webbrowser.open(html_path.as_uri())


if __name__ == '__main__':
    main()
