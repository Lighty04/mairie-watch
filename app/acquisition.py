"""Customer acquisition and CRM tracking system.

- Prospect management
- Outreach templates
- Conversion tracking
- Free trial onboarding
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class ProspectCategory(Enum):
    JOURNALIST = "journalist"
    COUNCILOR = "councilor"
    ACTIVIST = "activist"
    LAWYER = "lawyer"
    RESEARCHER = "researcher"
    OTHER = "other"

class ProspectStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    TRIAL = "trial"
    CONVERTED = "converted"
    DECLINED = "declined"
    DORMANT = "dormant"

@dataclass
class Prospect:
    id: int
    name: str
    email: Optional[str]
    twitter: Optional[str]
    organization: Optional[str]
    category: ProspectCategory
    city: str  # which city they care about
    interests: List[str]  # keywords/areas of interest
    status: ProspectStatus
    contacted_at: Optional[datetime]
    responded_at: Optional[datetime]
    notes: str
    created_at: datetime

# ---------------------------------------------------------------------------
# Pre-built prospect list (50 targets)
# ---------------------------------------------------------------------------

DEFAULT_PROSPECTS: List[Dict] = [
    # Journalists
    {"name": "Le Parisien — City Desk", "organization": "Le Parisien", "category": "journalist", "city": "paris", "interests": ["politique municipale", "subventions", "contrats"], "twitter": "@le_Parisien"},
    {"name": "20 Minutes Paris", "organization": "20 Minutes", "category": "journalist", "city": "paris", "interests": ["actualité locale", "transports", "urbanisme"], "twitter": "@20minutesParis"},
    {"name": "France 3 Paris Île-de-France", "organization": "France Télévisions", "category": "journalist", "city": "paris", "interests": ["politique", "environnement", "culture"], "email": "redaction.paris@francetv.fr"},
    {"name": "Mediapart Local", "organization": "Mediapart", "category": "journalist", "city": "paris", "interests": ["investigations", "corruption", "contrats publics"], "twitter": "@Mediapart"},
    {"name": "Bastamag", "organization": "Basta!", "category": "journalist", "city": "paris", "interests": ["environnement", "social", "justice"], "twitter": "@Bastamag"},
    {"name": "Politis", "organization": "Politis", "category": "journalist", "city": "paris", "interests": ["politique", "associations", "subventions"], "twitter": "@Politis"},
    {"name": "L'Humanité Local", "organization": "L'Humanité", "category": "journalist", "city": "paris", "interests": ["social", "logement", "syndicats"], "twitter": "@humanite_fr"},
    {"name": "Les Jours", "organization": "Les Jours", "category": "journalist", "city": "paris", "interests": ["enquêtes", "long format", "transparence"], "twitter": "@LesJoursFr"},
    {"name": "Arrêt sur Images", "organization": "Arrêt sur Images", "category": "journalist", "city": "paris", "interests": ["médias", "désinformation", "politique"], "twitter": "@arretsurimages"},
    {"name": "Actu.fr Paris", "organization": "Actu.fr", "category": "journalist", "city": "paris", "interests": ["actualité locale", "faits divers", "économie"]},
    
    # Councilors
    {"name": "Conseil de Paris — Opposition", "organization": "Paris City Council", "category": "councilor", "city": "paris", "interests": ["budget", "subventions", "urbanisme"]},
    {"name": "12e Arrondissement — Majority", "organization": "Mairie du 12e", "category": "councilor", "city": "paris", "interests": ["sports", "culture", "associations"]},
    {"name": "15e Arrondissement — Opposition", "organization": "Mairie du 15e", "category": "councilor", "city": "paris", "interests": ["logement", "transports", "commerce"]},
    {"name": "18e Arrondissement — Majority", "organization": "Mairie du 18e", "category": "councilor", "city": "paris", "interests": ["culture", "associations", "économie"]},
    {"name": "20e Arrondissement — Opposition", "organization": "Mairie du 20e", "category": "councilor", "city": "paris", "interests": ["logement", "santé", "éducation"]},
    {"name": "Marseille City Council", "organization": "Mairie de Marseille", "category": "councilor", "city": "marseille", "interests": ["ports", "tourisme", "transports"]},
    {"name": "Lyon City Council", "organization": "Mairie de Lyon", "category": "councilor", "city": "lyon", "interests": ["transports", "culture", "environnement"]},
    
    # Activists
    {"name": "Droit au Logement", "organization": "DAL", "category": "activist", "city": "paris", "interests": ["logement", "subventions", "urbanisme"], "twitter": "@DAL_France"},
    {"name": "Les Amis de la Terre", "organization": "Amis de la Terre", "category": "activist", "city": "paris", "interests": ["environnement", "climat", "énergie"], "twitter": "@amisdelaterre"},
    {"name": "Attac France", "organization": "Attac", "category": "activist", "city": "paris", "interests": ["justice fiscale", "privatisation", "contrats"], "twitter": "@attac_fr"},
    {"name": "CGT Île-de-France", "organization": "CGT", "category": "activist", "city": "paris", "interests": ["fonction publique", "santé", "éducation"], "twitter": "@CGT"},
    {"name": "Greenpeace France", "organization": "Greenpeace", "category": "activist", "city": "paris", "interests": ["climat", "pollution", "énergie"], "twitter": "@greenpeacefr"},
    {"name": "Emmaüs Solidarité", "organization": "Emmaüs", "category": "activist", "city": "paris", "interests": ["logement", "social", "subventions"], "twitter": "@emmaus_france"},
    {"name": "Secours Populaire", "organization": "Secours Populaire", "category": "activist", "city": "paris", "interests": ["social", "subventions", "associations"]},
    {"name": "Fondation Abbé Pierre", "organization": "Fondation Abbé Pierre", "category": "activist", "city": "paris", "interests": ["logement", "sans-abrisme", "subventions"], "twitter": "@AbbePierreFond"},
    {"name": "Utopia 56", "organization": "Utopia 56", "category": "activist", "city": "paris", "interests": ["migrants", "logement", "humanitaire"], "twitter": "@Utopia_56"},
    {"name": "Ligue des Droits de l'Homme", "organization": "LDH", "category": "activist", "city": "paris", "interests": ["droits civiques", "transparence", "libertés"], "twitter": "@LDH_Fr"},
    
    # Law firms
    {"name": "Cabinet XYZ — Marchés publics", "organization": "Cabinet XYZ", "category": "lawyer", "city": "paris", "interests": ["marchés publics", "contrats", "contentieux"]},
    {"name": "Urban Planning Consultants", "organization": "UPC", "category": "lawyer", "city": "paris", "interests": ["urbanisme", "permis", "décrets"]},
    {"name": "Public Affairs Group", "organization": "PAG", "category": "lawyer", "city": "paris", "interests": ["lobbying", "contrats", "subventions"]},
    {"name": "Droit & Ville", "organization": "Droit & Ville", "category": "lawyer", "city": "paris", "interests": ["droit local", "collectivités", "finances"]},
    {"name": "Avocats de la Ville", "organization": "Avocats de la Ville", "category": "lawyer", "city": "paris", "interests": ["contentieux", "marchés publics", "droit administratif"]},
    
    # Researchers
    {"name": "Sciences Po — Urban Studies", "organization": "Sciences Po", "category": "researcher", "city": "paris", "interests": ["urbanisme", "politique locale", "gouvernance"]},
    {"name": "Panthéon-Sorbonne — Public Law", "organization": "Paris 1", "category": "researcher", "city": "paris", "interests": ["droit public", "collectivités", "transparence"]},
    {"name": "INRAE — Public Policy", "organization": "INRAE", "category": "researcher", "city": "paris", "interests": ["politique publique", "environnement", "agriculture"]},
    {"name": "CNRS — Political Science", "organization": "CNRS", "category": "researcher", "city": "paris", "interests": ["science politique", "élections", "partis"]},
    {"name": "INED — Demography", "organization": "INED", "category": "researcher", "city": "paris", "interests": ["démographie", "logement", "migration"]},
]

# ---------------------------------------------------------------------------
# Outreach templates
# ---------------------------------------------------------------------------

OUTREACH_TEMPLATES: Dict[str, str] = {
    "journalist": """Subject: Alert tool for Paris municipal decisions — free trial

Hi {{ name }},

I saw your recent coverage of municipal decisions. We're building MairieWatch, an alert system that monitors decisions (subventions, appointments, contracts) from Paris city hall and all 20 arrondissements.

Currently tracking 20+ decisions/day with smart summaries and keyword alerts.

Would you be interested in a free trial? I can set up alerts for your specific beat.

Dashboard: http://192.168.0.16:8083
— MairieWatch Team""",

    "councilor": """Subject: Track decisions affecting your arrondissement

Hello {{ name }},

As a councilor, you might find this useful:

MairieWatch monitors all municipal decisions from the Conseil de Paris and arrondissement councils.

Get real-time alerts + weekly digests.

Free trial: http://192.168.0.16:8083
— MairieWatch Team""",

    "activist": """Subject: Monitor subventions & contracts in your cause area

Hi {{ name }},

MairieWatch tracks all municipal decisions including:
- Subventions to associations
- Public contracts
- Appointments to public boards

Set alerts for keywords and get notified within hours.

Free for activists: http://192.168.0.16:8083
— MairieWatch Team""",

    "lawyer": """Subject: Real-time monitoring of Paris public contracts

Hello {{ name }},

MairieWatch monitors all municipal decisions in real-time, including public contracts, subventions, and appointments.

Track competitors, identify opportunities, stay ahead.

Dashboard: http://192.168.0.16:8083
— MairieWatch Team""",

    "researcher": """Subject: Complete dataset of Paris municipal decisions

Hi {{ name }},

MairieWatch is building the most comprehensive dataset of Paris municipal decisions (subventions, appointments, contracts, urbanism).

Currently 20+ decisions/day, fully categorized and searchable.

Would you like API access for your research?

Contact us: http://192.168.0.16:8083/pricing
— MairieWatch Team""",
}

def render_template(template_name: str, prospect: Dict) -> str:
    """Render an outreach template for a prospect."""
    template = OUTREACH_TEMPLATES.get(template_name, OUTREACH_TEMPLATES["journalist"])
    
    # Simple variable substitution
    for key, value in prospect.items():
        placeholder = f"{{{{ {key} }}}}"
        if placeholder in template:
            template = template.replace(placeholder, str(value))
    
    return template

def get_template_for_category(category: str) -> str:
    """Get the appropriate template for a prospect category."""
    mapping = {
        "journalist": "journalist",
        "councilor": "councilor",
        "activist": "activist",
        "lawyer": "lawyer",
        "researcher": "researcher",
    }
    return mapping.get(category, "journalist")

# ---------------------------------------------------------------------------
# Conversion tracking
# ---------------------------------------------------------------------------

class ConversionTracker:
    """Track signup-to-conversion funnel."""
    
    def __init__(self):
        self.metrics = {
            "signups": 0,
            "trial_starts": 0,
            "trial_completions": 0,
            "pro_conversions": 0,
            "team_conversions": 0,
            "churned": 0,
        }
    
    def record_signup(self):
        self.metrics["signups"] += 1
    
    def record_trial_start(self):
        self.metrics["trial_starts"] += 1
    
    def record_trial_complete(self):
        self.metrics["trial_completions"] += 1
    
    def record_conversion(self, tier: str = "pro"):
        if tier == "pro":
            self.metrics["pro_conversions"] += 1
        elif tier == "team":
            self.metrics["team_conversions"] += 1
    
    def record_churn(self):
        self.metrics["churned"] += 1
    
    def get_funnel_stats(self) -> Dict:
        s = self.metrics
        return {
            **s,
            "trial_rate": round(s["trial_starts"] / max(s["signups"], 1) * 100, 1),
            "conversion_rate": round(s["pro_conversions"] / max(s["trial_starts"], 1) * 100, 1),
            "churn_rate": round(s["churned"] / max(s["pro_conversions"], 1) * 100, 1),
        }

# Global tracker instance
tracker = ConversionTracker()

# ---------------------------------------------------------------------------
# Trial onboarding sequence
# ---------------------------------------------------------------------------

TRIAL_ONBOARDING = [
    {
        "day": 0,
        "subject": "Welcome to MairieWatch — Your alerts are ready",
        "body": """Welcome to MairieWatch!

Your dashboard: http://192.168.0.16:8083

Next steps:
1. Create 2-3 alert rules for your interests
2. Explore the decision timeline
3. Set up your weekly digest preferences

Need help? Reply to this email.
""",
    },
    {
        "day": 2,
        "subject": "Your first alert digest",
        "body": """Here's what we found for you:

{{ alert_summary }}

Tip: You can create advanced alert rules with boolean operators and amount thresholds on the Pro plan.

View all alerts: http://192.168.0.16:8083/alerts
""",
    },
    {
        "day": 5,
        "subject": "How are your alerts working?",
        "body": """Quick check-in — how are your alerts performing?

- Are you getting too many false positives?
- Are we missing anything important?
- Would you like help refining your rules?

Reply to this email with feedback.

View your stats: http://192.168.0.16:8083/metrics
""",
    },
    {
        "day": 7,
        "subject": "Upgrade to Pro — Unlock unlimited alerts",
        "body": """Your free trial is ending soon.

Here's what you would have missed without MairieWatch:
- {{ missed_decisions }} decisions published this week
- {{ alerts_triggered }} matching your interests

Upgrade to Pro for:
✓ Unlimited alert rules
✓ Instant alerts (no 24h delay)
✓ Advanced filters (amount, boolean queries)
✓ Slack integration
✓ API access

€39/month — First month €19 (50% off)

Upgrade now: http://192.168.0.16:8083/pricing
""",
    },
]

def get_onboarding_email(day: int) -> Optional[Dict]:
    """Get the onboarding email for a specific day."""
    for email in TRIAL_ONBOARDING:
        if email["day"] == day:
            return email
    return None
