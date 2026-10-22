# AI-Powered Enterprise IT Ticket Management System

A runnable portfolio project demonstrating IT ticket creation, rule-based ticket classification, priority prediction, team routing, TF-IDF similarity search over historical tickets, SQLite persistence, status updates, metrics, and a responsive web dashboard.

## Requirements
- Python 3.10+ recommended
- VS Code (optional)
- Internet not required after packages are installed

## Run on Windows / PowerShell
Open this folder in VS Code. In the terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Then open:
- Dashboard: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## What it does
1. Creates an IT support ticket through a browser form or REST API.
2. Assigns a category and support team using a transparent keyword baseline.
3. Estimates priority using basic rules.
4. Suggests an approved-style troubleshooting checklist.
5. Retrieves similar sample incidents using TF-IDF cosine similarity (scikit-learn).
6. Stores tickets in SQLite.
7. Allows ticket status changes and shows dashboard metrics.

## Dataset
`data/tickets.csv` contains illustrative synthetic demo incidents. Do not treat it as real customer/company data.

## API quick examples
Create a ticket:
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/tickets -ContentType "application/json" -Body '{"title":"VPN is not connecting","description":"VPN fails after I changed my password","requester":"Demo User"}'
```
List tickets:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/tickets
```
Update status:
```powershell
Invoke-RestMethod -Method Patch "http://127.0.0.1:8000/api/tickets/1/status?status=In%20Progress"
```

## Architecture
Browser UI -> FastAPI -> triage module -> SQLite + historical ticket search -> recommended resolution -> engineer review.

## Important project limitations
- This version is a working baseline, not a production-grade autonomous resolver.
- Ticket categorization is keyword/rule-based, not a trained classifier.
- Historical retrieval uses TF-IDF, not neural embeddings or a vector database.
- It does not call Claude/OpenAI or another LLM by default, so no API key is needed.
- Confidence percentages are deliberately not fabricated.
- Before production use, add authentication, authorization, audit logs, monitoring, tests, secrets management, company-approved knowledge sources, and human approval. Never load confidential tickets from another company without authorization.

## Next upgrade ideas
- Train and evaluate a supervised classifier on labeled, authorized tickets.
- Add sentence-transformer embeddings + FAISS/Chroma for semantic retrieval.
- Add an optional LLM adapter with environment-based API keys, citations to retrieved documents, and prompt-injection defenses.
- Add role-based access, audit logging, Docker, and deployment.
