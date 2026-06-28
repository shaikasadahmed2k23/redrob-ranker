"""
Hand-curated reference tables for the Redrob candidate pool.

The candidate pool draws from a closed, enumerable universe of companies (63),
titles (48), and skills (133). Rather than relying purely on fuzzy text
matching, we classify each of these explicitly. This is more transparent,
faster, and easier to defend than asking an embedding model to infer
"is Infosys a product company?" -- a question it will get wrong as often
as right.

These tables were built by enumerating every distinct value across the full
100K-candidate pool (see notebooks/01_explore_data.py) and classifying each
by hand against the job description's stated preferences and disqualifiers.
"""

# ---------------------------------------------------------------------------
# COMPANY CLASSIFICATION
# ---------------------------------------------------------------------------
# company_type values:
#   "ai_native"      - AI/ML is the company's core product (best signal)
#   "big_tech"        - FAANG-scale product company, strong eng culture
#   "product_india"   - Indian product/internet company (unicorn-ish)
#   "product_other"   - Other recognizable product company
#   "saas"             - B2B SaaS product company
#   "consulting"        - IT services / staffing / consulting (JD disqualifier
#                         territory if it's the *entire* career)
#   "fictional"        - Joke/placeholder companies (Acme Corp, Hooli, Pied Piper,
#                         Stark Industries, Wayne Enterprises, Globex Inc,
#                         Initech, Dunder Mifflin). Treated as ordinary
#                         "unverifiable / generic" employers -- not auto-penalized,
#                         just gets no company-prestige bonus, since we cannot
#                         verify anything about them. (These read as filler /
#                         control-group employers in this synthetic dataset.)
#
# is_ai_relevant_industry: True if the company's core business is AI/ML/NLP/IR,
# which the JD treats as a much stronger signal than a generic tech company.

COMPANY_TABLE = {
    # --- Big tech / global product companies ---
    "Google":        {"type": "big_tech", "ai_relevant": True},
    "Meta":           {"type": "big_tech", "ai_relevant": True},
    "Amazon":         {"type": "big_tech", "ai_relevant": False},
    "Microsoft":      {"type": "big_tech", "ai_relevant": True},
    "Apple":          {"type": "big_tech", "ai_relevant": False},
    "Netflix":        {"type": "big_tech", "ai_relevant": True},   # famous for recsys
    "LinkedIn":       {"type": "big_tech", "ai_relevant": True},   # famous for search/ranking
    "Salesforce":     {"type": "big_tech", "ai_relevant": False},
    "Adobe":          {"type": "big_tech", "ai_relevant": False},
    "Uber":           {"type": "big_tech", "ai_relevant": False},

    # --- AI-native companies (core product IS AI/ML/NLP/IR) ---
    "Krutrim":        {"type": "ai_native", "ai_relevant": True},
    "Sarvam AI":      {"type": "ai_native", "ai_relevant": True},
    "Aganitha":       {"type": "ai_native", "ai_relevant": True},
    "Mad Street Den": {"type": "ai_native", "ai_relevant": True},
    "Observe.AI":     {"type": "ai_native", "ai_relevant": True},
    "Yellow.ai":      {"type": "ai_native", "ai_relevant": True},
    "Haptik":         {"type": "ai_native", "ai_relevant": True},
    "Rephrase.ai":    {"type": "ai_native", "ai_relevant": True},
    "Saarthi.ai":     {"type": "ai_native", "ai_relevant": True},
    "Verloop.io":     {"type": "ai_native", "ai_relevant": True},
    "Locobuzz":       {"type": "ai_native", "ai_relevant": True},
    "Glance":         {"type": "ai_native", "ai_relevant": True},
    "Niramai":        {"type": "ai_native", "ai_relevant": True},   # HealthTech AI
    "Wysa":           {"type": "ai_native", "ai_relevant": True},   # HealthTech AI
    "Genpact AI":     {"type": "ai_native", "ai_relevant": True},   # branded AI services arm

    # --- Indian product companies (unicorns / well-known consumer/fintech) ---
    "Flipkart":       {"type": "product_india", "ai_relevant": False},
    "Paytm":          {"type": "product_india", "ai_relevant": False},
    "PhonePe":        {"type": "product_india", "ai_relevant": False},
    "Razorpay":       {"type": "product_india", "ai_relevant": False},
    "Swiggy":         {"type": "product_india", "ai_relevant": False},
    "Zomato":         {"type": "product_india", "ai_relevant": False},
    "Ola":            {"type": "product_india", "ai_relevant": False},
    "Meesho":         {"type": "product_india", "ai_relevant": False},
    "Nykaa":          {"type": "product_india", "ai_relevant": False},
    "CRED":           {"type": "product_india", "ai_relevant": False},
    "Dream11":        {"type": "product_india", "ai_relevant": False},
    "InMobi":         {"type": "product_india", "ai_relevant": False},
    "PolicyBazaar":   {"type": "product_india", "ai_relevant": False},
    "PharmEasy":      {"type": "product_india", "ai_relevant": False},
    "BYJU'S":         {"type": "product_india", "ai_relevant": False},
    "Unacademy":      {"type": "product_india", "ai_relevant": False},
    "Vedantu":        {"type": "product_india", "ai_relevant": False},
    "upGrad":         {"type": "product_india", "ai_relevant": False},

    # --- SaaS product companies ---
    "Freshworks":     {"type": "saas", "ai_relevant": False},
    "Zoho":           {"type": "saas", "ai_relevant": False},

    # --- IT services / consulting (JD disqualifier territory if ENTIRE career) ---
    "TCS":            {"type": "consulting", "ai_relevant": False},
    "Infosys":        {"type": "consulting", "ai_relevant": False},
    "Wipro":          {"type": "consulting", "ai_relevant": False},
    "Accenture":      {"type": "consulting", "ai_relevant": False},
    "Cognizant":      {"type": "consulting", "ai_relevant": False},
    "Capgemini":      {"type": "consulting", "ai_relevant": False},
    "HCL":            {"type": "consulting", "ai_relevant": False},
    "Mphasis":        {"type": "consulting", "ai_relevant": False},
    "Tech Mahindra":  {"type": "consulting", "ai_relevant": False},
    "Mindtree":       {"type": "consulting", "ai_relevant": False},

    # --- Fictional / placeholder employers (synthetic-data filler) ---
    "Acme Corp":         {"type": "fictional", "ai_relevant": False},
    "Globex Inc":        {"type": "fictional", "ai_relevant": False},
    "Hooli":             {"type": "fictional", "ai_relevant": False},
    "Initech":           {"type": "fictional", "ai_relevant": False},
    "Pied Piper":        {"type": "fictional", "ai_relevant": False},
    "Stark Industries":  {"type": "fictional", "ai_relevant": False},
    "Wayne Enterprises": {"type": "fictional", "ai_relevant": False},
    "Dunder Mifflin":    {"type": "fictional", "ai_relevant": False},
}

CONSULTING_COMPANIES = {c for c, v in COMPANY_TABLE.items() if v["type"] == "consulting"}

# Company-type base scores (0-1), used in the company-quality component.
COMPANY_TYPE_SCORE = {
    "ai_native":     1.00,
    "big_tech":      0.90,
    "product_india": 0.75,
    "product_other": 0.70,
    "saas":          0.65,
    "consulting":    0.35,
    "fictional":     0.55,   # unverifiable, treated as neutral-generic
}


def company_info(company_name: str) -> dict:
    return COMPANY_TABLE.get(company_name, {"type": "product_other", "ai_relevant": False})


# ---------------------------------------------------------------------------
# TITLE CLASSIFICATION
# ---------------------------------------------------------------------------
# title_tier: 0 (irrelevant) to 5 (perfect match) relevance to the JD
# (Senior AI Engineer doing ranking/retrieval/embeddings work).

TITLE_TIER = {
    # Tier 5: exact/near-exact match to the role
    "Senior AI Engineer": 5,
    "Senior ML Engineer — Search & Ranking": 5,
    "Lead AI Engineer": 5,
    "Staff Machine Learning Engineer": 5,
    "Search Engineer": 5,
    "Recommendation Systems Engineer": 5,

    # Tier 4: strong adjacent senior ML/AI roles
    "Senior Machine Learning Engineer": 4,
    "Senior NLP Engineer": 4,
    "Senior Applied Scientist": 4,
    "Senior Software Engineer (ML)": 4,
    "ML Engineer": 4,
    "Machine Learning Engineer": 4,
    "NLP Engineer": 4,
    "Applied ML Engineer": 4,

    # Tier 3: relevant ML/AI but junior, or AI-adjacent without seniority signal
    "AI Engineer": 3,
    "AI Research Engineer": 3,   # relevant domain, but JD explicitly distrusts pure-research path
    "AI Specialist": 3,
    "Computer Vision Engineer": 3,   # relevant ML, but JD wants NLP/IR not CV
    "Junior ML Engineer": 3,
    "Senior Data Scientist": 3,
    "Data Scientist": 3,

    # Tier 2: technical, adjacent, could plausibly transition
    "Senior Data Engineer": 2,
    "Data Engineer": 2,
    "Senior Software Engineer": 2,
    "Software Engineer": 2,
    "Analytics Engineer": 2,
    "Data Analyst": 2,
    "Backend Engineer": 2,
    "Full Stack Developer": 2,
    "Cloud Engineer": 2,
    "DevOps Engineer": 2,

    # Tier 1: technical but far from the role's core (frontend/mobile/QA/etc.)
    "Frontend Engineer": 1,
    "Mobile Developer": 1,
    "QA Engineer": 1,
    "Java Developer": 1,
    ".NET Developer": 1,

    # Tier 0: unrelated disciplines entirely
    "HR Manager": 0,
    "Sales Executive": 0,
    "Mechanical Engineer": 0,
    "Business Analyst": 0,
    "Accountant": 0,
    "Civil Engineer": 0,
    "Project Manager": 0,
    "Graphic Designer": 0,
    "Marketing Manager": 0,
    "Operations Manager": 0,
    "Content Writer": 0,
    "Customer Support": 0,
}

PURE_RESEARCH_TITLES = {"AI Research Engineer"}


def title_tier(title: str) -> int:
    return TITLE_TIER.get(title, 1)  # unseen titles treated as weakly technical


# ---------------------------------------------------------------------------
# SKILL CLASSIFICATION
# ---------------------------------------------------------------------------
# skill_weight: 0-1, relevance of the skill to "embeddings / retrieval / ranking /
# LLMs / hybrid search / production ML" as the JD defines the core need.
# "framework_surface" skills (LangChain, RAG-as-a-buzzword) are flagged separately
# since the JD explicitly distrusts candidates whose AI exposure is JUST these.

CORE_SKILLS = {
    # Retrieval / ranking / search infra -- the JD's #1 ask
    "Embeddings": 1.0, "Vector Search": 1.0, "Vector Representations": 1.0,
    "Semantic Search": 1.0, "FAISS": 1.0, "Pinecone": 1.0, "Weaviate": 1.0,
    "Qdrant": 1.0, "Milvus": 1.0, "pgvector": 1.0, "Elasticsearch": 0.95,
    "OpenSearch": 0.95, "BM25": 0.95, "Information Retrieval": 1.0,
    "Information Retrieval Systems": 1.0, "Ranking Systems": 1.0,
    "Learning to Rank": 1.0, "Recommendation Systems": 0.95,
    "Search Infrastructure": 1.0, "Search Backend": 0.95,
    "Search & Discovery": 0.9, "Indexing Algorithms": 0.9,
    "Sentence Transformers": 0.95, "Text Encoders": 0.9,
    "Content Matching": 0.7, "Haystack": 0.85,

    # LLMs / fine-tuning -- valued, but JD also wants depth pre-dating the hype
    "LLMs": 0.8, "Fine-tuning LLMs": 0.85, "LoRA": 0.8, "QLoRA": 0.8,
    "PEFT": 0.8, "Prompt Engineering": 0.55,  # explicitly the "surface" skill
    "RAG": 0.6,  # explicitly the "surface" skill per JD
    "LangChain": 0.45,  # JD explicitly distrusts LangChain-tutorial-only profiles
    "LlamaIndex": 0.5,
    "Hugging Face Transformers": 0.8,
    "Model Adaptation": 0.75,

    # Core ML / production ML
    "Machine Learning": 0.7, "Deep Learning": 0.75, "PyTorch": 0.75,
    "TensorFlow": 0.7, "MLOps": 0.75, "MLflow": 0.65, "Kubeflow": 0.65,
    "Feature Engineering": 0.6, "scikit-learn": 0.55, "Reinforcement Learning": 0.6,
    "Statistical Modeling": 0.5, "Open-source ML libraries": 0.5,

    # NLP specifically (JD wants NLP/IR exposure)
    "NLP": 0.9, "Natural Language Processing": 0.9, "Document Processing": 0.6,

    # Adjacent ML domains JD treats as a yellow flag if that's ALL someone has
    "Computer Vision": 0.35, "Image Classification": 0.3, "Object Detection": 0.3,
    "YOLO": 0.3, "Speech Recognition": 0.3, "ASR": 0.3, "TTS": 0.3,
    "GANs": 0.35, "Diffusion Models": 0.35, "CNN": 0.35,

    # Production / systems engineering (the "shipper" half of the JD)
    "Python": 0.7, "Data Pipelines": 0.45, "ETL": 0.35, "Spark": 0.4,
    "Kafka": 0.4, "Airflow": 0.4, "Docker": 0.4, "Kubernetes": 0.45,
    "Microservices": 0.4, "REST APIs": 0.3, "FastAPI": 0.4, "gRPC": 0.35,
    "CI/CD": 0.3, "Workflow Orchestration": 0.35, "Databricks": 0.4,
    "Apache Beam": 0.35, "Apache Flink": 0.35, "Time Series": 0.4,
    "Forecasting": 0.35, "BigQuery": 0.3, "Snowflake": 0.3, "dbt": 0.3,
    "Redis": 0.25, "MongoDB": 0.2, "PostgreSQL": 0.2, "AWS": 0.3,
    "GCP": 0.3, "Azure": 0.3, "Terraform": 0.25, "BentoML": 0.45,
    "Weights & Biases": 0.45,
}

# Skills with essentially zero relevance to this JD (web/frontend/generic biz)
# -> default weight 0.05 for anything not listed above.
DEFAULT_SKILL_WEIGHT = 0.05


def skill_weight(skill_name: str) -> float:
    return CORE_SKILLS.get(skill_name, DEFAULT_SKILL_WEIGHT)


FRAMEWORK_SURFACE_SKILLS = {"LangChain", "RAG", "Prompt Engineering", "LlamaIndex"}

# ---------------------------------------------------------------------------
# LOCATION CLASSIFICATION
# ---------------------------------------------------------------------------
TIER1_PREFERRED = {"Pune", "Noida"}  # explicit JD preference
TIER1_WELCOME = {"Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Noida"}  # JD "welcome to apply"


def location_score(location: str, country: str) -> float:
    if country != "India":
        return 0.35  # case-by-case, no visa sponsorship -- not zero, but a real penalty
    city = location.split(",")[0].strip()
    if city in TIER1_PREFERRED:
        return 1.0
    if city in TIER1_WELCOME:
        return 0.85
    return 0.6  # other India cities -- JD says hybrid/relocation candidates from Tier-1 cities
