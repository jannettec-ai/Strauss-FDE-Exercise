# Strauss Procurement Negotiation Prep Packet

An AI-powered tool that auto-generates a one-page negotiation prep packet
ahead of each upcoming supplier meeting, combining email history, contract
terms, and commodity price benchmarks into a single briefing view.

Built as a Forward Deployed Engineer take-home exercise for Strauss Group.

---

## What it does

The Strauss procurement team spends significant time before each supplier
negotiation manually pulling together email history, contract terms, and
price data from separate sources. This tool automates that assembly,
generating a structured packet per meeting that surfaces key facts,
flags conflicts between emails and contract terms, and lets the analyst
correct or override any field before walking into the room.

---

## Live demo

https://strauss-procurement.streamlit.app/

---

## Repo structure

```
strauss-fde-exercise/
├── CLAUDE.md                        # Claude Code project context
├── .claude/rules/metrics.md         # KPI data dictionary
├── data/
│   ├── suppliers-roster.md          # 8 suppliers, categories, messiness profiles
│   ├── calendar.csv                 # 14 upcoming negotiation meetings
│   ├── emails/                      # Synthetic supplier email threads (JSON)
│   ├── contracts/                   # Synthetic supplier contracts (markdown)
│   └── prices/                      # Commodity price CSVs (cocoa, sugar, dairy)
├── docs/
│   ├── problem-framing.md           # Part 1: pain points, KPIs, stakeholders
│   ├── solution.md                  # Part 2: pitch, architecture, tradeoffs
│   └── strategy.md                  # Part 4: rollout, resistance plan, ROI case
├── scripts/
│   └── pull_prices.py               # One-time price data pull (yfinance)
└── src/
    ├── extraction.py                # Email + contract parsing via Claude API
    ├── packet_generator.py          # Assembles packet per meeting
    └── app.py                       # Streamlit interface
```

---

## Running locally

**Prerequisites**: Python 3.10+, an Anthropic API key

**1. Clone the repo**
```bash
git clone https://github.com/your-username/strauss-fde-exercise.git
cd strauss-fde-exercise
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set your Anthropic API key**
```bash
# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-xxxxxxxx"

# Mac/Linux
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

**5. Run the app**
```bash
streamlit run src/app.py
```

---

## Deploying to Streamlit Cloud (for shared access)

This is the recommended way to share the app without requiring others to
set up an API key or run Python locally.

**1. Push the repo to GitHub** (make sure no API keys are in any file)

**2. Go to [share.streamlit.io](https://share.streamlit.io)** and sign in
with GitHub

**3. Click "New app"**, select your repo, set the main file path to
`src/app.py`

**4. Add your API key as a secret**:
- In the app settings, go to "Secrets"
- Add the following:
```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```

**5. Deploy.** Streamlit Cloud will install dependencies from
`requirements.txt` automatically and give you a shareable URL.

The API key lives in Streamlit Cloud's secrets manager, it never touches
the repo or any file you share.

---

## Data notes

All data is synthetic, generated for this exercise. No real Strauss
supplier data, contracts, or internal communications are used anywhere
in this repo.

Commodity prices (cocoa, sugar, dairy) are real public market data pulled
once via yfinance from Yahoo Finance and saved as static CSVs. To refresh:
```bash
python scripts/pull_prices.py
```

---

## Exercise documentation

Full written responses for Parts 1, 2, and 4 of the exercise are in
`docs/`. The data dictionary governing all KPI calculations is in
`.claude/rules/metrics.md`.
