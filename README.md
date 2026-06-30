# **HOA Auditor Agent**

A multi-agent auditing system built using the Google Agent Development Kit (ADK) framework and gemini-2.5-flash natively to audit Homeowner Association (HOA) legal and financial documents.

## **🏗️ System Architecture**

Our **Dual-Track Caching Pipeline** acts as an enterprise-grade **Token Blocker** to insulate operating margins from runaway LLM API costs. If a document package hash is already cached, it bypasses the live model entirely, serving structured results instantly.

```text
                     ┌─────────────────────────────────┐  
                     │   1. Document Ingestion Layer   │  
                     │    - CC&Rs, Bylaws, Financials  │  
                     └────────────────┬────────────────┘  
                                      │  
                                      ▼  
                     ┌─────────────────────────────────┐  
                     │     Deterministic MD5 Hash      │  
                     │   (Unique Cryptographic Sig)    │  
                     └────────────────┬────────────────┘  
                                      │  
                                      ▼  
                    /───────────────────────────────────\  
                   <   Active Environment Variables?     >  
                    \─────────────────┬─────────────────/  
                                      │  
              ┌───────────────────────┴───────────────────────┐  
              ▼ YES                                           ▼ NO (Sandbox Mode)  
  ┌───────────────────────────┐                 ┌───────────────────────────┐  
  │   Level 1: Cloud Cache    │                 │  Level 2: Sandbox Cache   │  
  │   - Query Supabase DB     │                 │  - Query .local_cache.json│  
  └───────────┬───────────────┘                 └─────────────┬─────────────┘  
              │                                               │  
      ┌───────┴───────┐                               ┌───────┴───────┐  
      ▼               ▼                               ▼               ▼  
  [Cache Hit]    [Cache Miss]                     [Cache Hit]    [Cache Miss]  
      │               │                               │               │  
      │               ▼                               │               ▼  
      │       ┌───────────────────────────┐           │       ┌───────────────────────────┐  
      │       │  Check Level 2 Cache      │           │       │   API Key Provided?       │  
      │       │  - Query .local_cache.json│           │       └───────┬───────────┬───────┘  
      │       └───────┬───────────┬───────┘           │               ▼ YES       ▼ NO  
      │               ▼           ▼                   │               │           │  
      │          [Cache Hit]  [Cache Miss]            │               │           ▼  
      │               │           │                   │               │     [Simulation Fail/  
      │               │           ▼                   │               │      Error Response]  
      │               │       ┌───────────┐           │               │  
      │               │       │ Gemini API│           │               │  
      │               │       └─────┬─────┘           │               │  
      ▼               ▼             ▼                 ▼               ▼  
┌───────────────────────────────────────────────────────────────────────────┐  
│                       Interactive UI & Dashboard                          │  
│         - Dynamic Risk Cards | Compliance RCW Checklists | Anchors        │  
└───────────────────────────────────────────────────────────────────────────┘
```

## **⚡ Evaluator Quick Start**

To avoid configuration overhead and run the audit dashboard instantly, we provide a **Dual-Track Evaluation Model**. You can choose to run this fully offline with zero setup, or activate your API keys to see live generations.

| Track | Target Audience | Setup Effort | Key Required | Caching Engine Used |
| :---- | :---- | :---- | :---- | :---- |
| **Track A: Lightning Offline (Recommended)** | Judges / Quick Reviews | **< 60 Seconds** | **None** | Reads precompiled signatures directly from app/.local_cache.json |
| **Track B: Production Online** | Advanced Review / Live Testing | **~3-5 Mins** | GEMINI_API_KEY, optional Supabase url/key | Executes live multi-agent calls and updates dual caches |

### **Option A: Lightning Offline Setup (Run in under 60 seconds)**

1. **Clone & Setup:**  
   ```bash
   git clone https://github.com/layclough/kaggle_submission_hoa_auditor.git
   cd kaggle_submission_hoa_auditor
   uv sync
   ```

2. **Execute Terminal Run Command (No environment variables required!):**  
   ```bash
   PYTHONPATH=. uv run streamlit run app/ui.py
   ```

   *The Streamlit dashboard will spin up instantly. It matches our mock document fingerprints, pulls the saved response directly from the sandbox cache file, and loads the complete audit evaluation dashboard in milliseconds with **zero API or Database setup friction**.*

### **Option B: Production Online Setup**

To execute live multi-agent audits on custom or modified document inputs:

1. **Configure Environment Variables:**  
   Create a `.env` file inside your `app/` folder matching the blueprint in `app/.env.example`:  
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here

   # Optional Cloud Caching Layer variables:
   SUPABASE_URL=your_supabase_project_url_here
   SUPABASE_KEY=your_supabase_anon_public_key_here
   ```

2. **Deploy Cloud Caching Tables (Optional):**  
   If using Supabase, run the script in database/schema.sql via your **Supabase SQL Editor** to initialize the cache table and row-level security policy.  
3. **Run Live Evaluation:**  
   ```bash
   PYTHONPATH=. uv run streamlit run app/ui.py
   ```

   *The system detects active keys, processes your updated mock documents, issues live structural model requests, and stores the new audits securely across both your local sandbox and Supabase cloud tables.*

## **💡 Core Business Value & Problem Space**

Reviewing Homeowner Association (HOA) documentation is one of the highest-friction steps in a real estate transaction. Buyers are routinely handed massive, unorganized text dumps spanning 300+ pages of complex legal jargon. Hidden inside this noise are critical liabilities—such as structural funding deficits, outstanding accounts payable, or strict property restrictions—that can lead to immediate buyer regret or stall mortgage timelines entirely.

This application acts as a compliance guardrail, ensuring that real estate professionals and homebuyers can evaluate property risk safely while systematically cross-referencing files against state-level mandates.

## **🛠️ Key Architectural & Product Features**

* **LLM Core & ADK Routing:** Powered by gemini-2.5-flash utilizing the Google ADK framework to route specialized tasks cleanly across an executive synthesizer root agent, a financial specialist, and a legal specialist.  
* **The Token Blocker (Cost Insulation Caching Layer):** Implements a robust dual-layer cryptographic fingerprinting system. When a document package is analyzed, a unique MD5 text hash is generated.  
  * **Level 1 (Local Sandbox Cache):** Automatically checks an offline JSON file for a matching signature.  
  * **Level 2 (Production Cloud Cache):** Optionally checks a **Supabase** backend if database credentials are provided.  
  * Identical packages bypass live LLM generation completely, delivering instant results from the database cache at **0 token cost** and near-zero latency, protecting the application's operating margins.  
* **State Compliance Guardrails:** The application explicitly cross-references data against a formal state regulation framework (such as Washington State's WUCIOA RCW 64.90.640). It verifies that every statutory disclosure requirement a seller is legally mandated to provide is present, automatically flagging missing items as critical legal vulnerabilities.  
* **Real-World Data Ingestion Flexibility:** Built with a variable-input ingestion layer that handles diverse condo disclosure packages seamlessly—whether a specific building provides 5 massive text blocks or 15 highly atomized documents.  
* **Interactive Frontend Experience:** A clean, multi-tab **Streamlit** dashboard that pulls the cached data directly, rendering actionable checklists, urgent legal/financial risk cards, and explicit source anchors for buyers.

## **📂 Project Structure**

```text
.
├── README.md
├── agents.json                        # Core agents definition/discovery configuration
├── pyproject.toml                     # Project packaging and dependencies
├── uv.lock                            # Fully resolved project lockfile
├── app/
│   ├── __init__.py                    # Initializes the ADK App
│   ├── agent.py                       # Defines executive_synthesizer (Root), financial_specialist, legal_specialist
│   ├── ui.py                          # Streamlit frontend user interface dashboard
│   ├── supabase_client.py             # Supabase token-blocker database interaction client
│   ├── tools.py                       # Registers HOA tools for the ADK agents
│   └── .env.example                   # Generic environment variable blueprint (Safe to commit)
├── database/
│   └── schema.sql                     # Supabase SQL initialization commands & security policy
├── system/
│   └── schemas/
│       └── report_manifest.yaml       # Report Schema v2.0 validation manifest
├── tools/
│   ├── __init__.py
│   └── hoa_tools.py                   # Implements tool functions (read_mcp_document_chunk, validate_cross_reference)
└── tests/
    └── eval/
        ├── eval_config.yaml           # Day 4 evaluation config (metrics & thresholds)
        └── datasets/
            └── basic-dataset.json     # Day 4 evaluation test cases
```
