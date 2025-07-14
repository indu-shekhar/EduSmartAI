Comprehensive Windows-Native Implementation Plan  
“Agentic RAG Educational Chatbot” – Flask + LlamaIndex + Gemini  
(Target: Windows 10/11, Python virtual-environment; NO Docker / WSL)  
════════════════════════════════════════════════════════════

0. 30-Second Executive Summary  
• A modular Flask web app that provides a ChatGPT-like study assistant, driven by a Retrieval-Augmented Generation (RAG) pipeline (LlamaIndex + Gemini).  
• Runs completely on Windows using a local Python virtual-environment (.venv).  
• Waitress is the production WSGI server; PowerShell / Task Scheduler replace Bash / cron.  
• Vector store = Chroma (pure Python) or FAISS (if you install the conda wheel).  
• All secrets live in a .env file and are loaded via python-dotenv.  
• PDF ingestion is triggered manually or on a schedule with Windows Task Scheduler.  

The remaining sections give you an end-to-end roadmap, mirroring the earlier Linux plan but fully adapted to Windows-native development.

────────────────────────────────────────────────────────────
1. High-Level Architecture   (unchanged, OS-agnostic)
────────────────────────────────────────────────────────────
Browser ⇄ Flask REST / HTMX endpoints  
│     ├─ Chat blueprint  (/chat, /history)  
│     ├─ RAG  blueprint  (/rag/query, /rag/summary)  
│     ├─ File blueprint  (/upload, /download/<id>)  
│     └─ Admin blueprint (/re-ingest, /health)  
│  
└─ Services Layer (singletons)  
      ├─ LlamaIndexService   │ Vector store (Chroma/FAISS)  
      ├─ ConversationService │ Chat history (SQLite)  
      └─ PDFIngestionPipeline  
Data Layer → SQLAlchemy ORM  

────────────────────────────────────────────────────────────
2. Repository Layout
────────────────────────────────────────────────────────────
agentic-rag-flask/                    # root Git repo  
├─ app/                               # Flask package  
│  ├─ __init__.py      ── create_app() + blueprint registry  
│  ├─ config.py        ── global Config / DevConfig / ProdConfig  
│  ├─ blueprints/      ── chat.py, rag.py, file.py, admin.py  
│  ├─ services/        ── llama_index_service.py, pdf_ingestion.py, …  
│  ├─ models/          ── database.py, chat_message.py, file.py, …  
│  ├─ templates/       ── base.html, chat.html, etc.  
│  └─ static/          ── css/, js/, uploads/  
├─ books/                            # put your PDFs here  
├─ storage/                          # vector store persists here (auto)  
├─ scripts/                          # Windows helper scripts  
│  ├─ activate_venv.bat              (call .venv\Scripts\activate)  
│  ├─ run_dev.ps1                    (sets env vars + flask run)  
│  ├─ ingest.ps1                     (python ingest.py --refresh)  
│  └─ schedule_reingest.xml          (Task Scheduler definition)  
├─ ingest.py                         # CLI to build / refresh index  
├─ requirements.txt  
├─ .env.example                      # sample ENV vars  
├─ README.md                         # step-by-step instructions  
└─ tests/                            # pytest suite  

────────────────────────────────────────────────────────────
3. Environment & Dependencies
────────────────────────────────────────────────────────────
A. Install prerequisites (once)  
1. Python 3.11 for Windows (enable “Add to PATH”).  
2. Visual Studio Build Tools 2022 → “C++ build tools” workload  
   (needed only if you compile FAISS yourself).  

B. Create & activate virtual-env  
CMD > py -m venv .venv  
CMD > call .venv\Scripts\activate.bat  
(PowerShell > .\.venv\Scripts\Activate.ps1)  

C. Install libraries  
pip install -r requirements.txt  

requirements.txt (excerpt, Windows-friendly)  
Flask==3.*  
Flask-SQLAlchemy  
Flask-CORS  
python-dotenv  
waitress              # WSGI server for Windows  
llama-index-core  
llama-index-llms-gemini  
llama-index-embeddings-gemini  
chromadb>=0.4.15      # pure-python vector db  
# optional: conda install -c pytorch faiss-cpu  
PyPDF2, pdfplumber, pdfminer-six  
python-magic-bin      # Windows build of libmagic  
pywin32               # Windows file locking  
pytest, pytest-asyncio, black, flake8 (dev)

D. .env contents  
GEMINI_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXX  
FLASK_ENV      = development  
EMBEDDING_DB   = chromadb       # or faiss  
VECTOR_DIR     = ./storage  
UPLOAD_FOLDER  = ./app/static/uploads  
PORT           = 8000  

────────────────────────────────────────────────────────────
4. Per-Machine Setup Scripts
────────────────────────────────────────────────────────────
scripts\activate_venv.bat
@echo off  
call %~dp0..\.\.venv\Scripts\activate.bat  
echo Virtual-env activated.

scripts\run_dev.ps1
param([switch]$RefreshIndex)  
$env:FLASK_APP = "app"  
$env:FLASK_DEBUG = "1"  
if ($RefreshIndex) { python ingest.py --refresh }  
flask run --port 8000 --reload  

Double-click run_dev.ps1 to start hot-reloading dev server.

────────────────────────────────────────────────────────────
5. Offline Ingestion Pipeline (Windows)
────────────────────────────────────────────────────────────
• Run manually:  powershell .\scripts\ingest.ps1  
• Or schedule daily:  
  schtasks /Create /TN "RAG\Reingest" /XML scripts\schedule_reingest.xml

Key code differences  
from pathlib import Path  
books_dir = Path(os.getenv("BOOKS_DIR", "./books")).resolve()  
...  # rest of LlamaIndex logic identical

────────────────────────────────────────────────────────────
6. LlamaIndex Service Layer  (identical logic)
────────────────────────────────────────────────────────────
• embed_model = GeminiEmbedding(model_name="models/embedding-001")  
• storage_context loads from VECTOR_DIR (Windows path ok via pathlib).  
• Provide ask(), summary(), compare() methods; return markdown + citations.

────────────────────────────────────────────────────────────
7. Flask Backend Details
────────────────────────────────────────────────────────────
7.1 Config (Windows-safe defaults)  
class Config:  
    SQLALCHEMY_DATABASE_URI = "sqlite:///chat.db"  
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "./app/static/uploads")).resolve()  
    VECTOR_DIR = Path(os.getenv("VECTOR_DIR", "./storage")).resolve()  

7.2 Run modes  
• Development:  flask run --reload --port 8000  
• Production:   waitress-serve --port=%PORT% "app:create_app()"

7.3 Background tasks  
• For lightweight ingestion after uploads: use APScheduler “BackgroundScheduler”.  
• Heavy workloads → Celery + Redis inside WSL2 or external Linux box (not required for PoC).

────────────────────────────────────────────────────────────
8. Front-End (Bootstrap 5 + HTMX)
────────────────────────────────────────────────────────────
HTML/JS identical.  No Windows-specific work needed.

────────────────────────────────────────────────────────────
9. Educational “Routes” (agent skills) – unchanged
────────────────────────────────────────────────────────────
/rag/query (default QA)  
/rag/summary  
/rag/compare  
Router agent chooses if endpoint not explicitly called.

────────────────────────────────────────────────────────────
10. Persistence & Chat History
────────────────────────────────────────────────────────────
SQLite file chat.db resides in project root; no extra drivers.  
Windows Defender automatically backs up via File History (optional).

────────────────────────────────────────────────────────────
11. Security & Compliance   (Windows notes)
────────────────────────────────────────────────────────────
• Do NOT commit .env or chat.db.  
• By default Windows Defender scans all writes, so clamd is optional.  
• If long paths cause errors, enable “LongPathsEnabled = 1” in Registry.

────────────────────────────────────────────────────────────
12. Testing Strategy
────────────────────────────────────────────────────────────
pytest  
pytest-asyncio  
vcrpy for Gemini stubbing  

Run locally:  
.\.venv\Scripts\activate  
pytest -q

GitHub Actions (windows-latest) sample provided earlier.

────────────────────────────────────────────────────────────
13. Automation with Windows Task Scheduler
────────────────────────────────────────────────────────────
Example schedule_reingest.xml (excerpt)
<RegistrationInfo><Description>Refresh RAG index</Description></RegistrationInfo>
<Triggers><CalendarTrigger><StartBoundary>2024-01-01T02:00:00</StartBoundary><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
<Actions><Exec><Command>powershell</Command><Arguments>-ExecutionPolicy Bypass -File "C:\path\to\scripts\ingest.ps1"</Arguments></Exec></Actions>

Import:  schtasks /Create /XML schedule_reingest.xml /TN "RAG\Reingest"

────────────────────────────────────────────────────────────
14. Run / Deploy Checklist  (no Docker)
────────────────────────────────────────────────────────────
1. git clone https://github.com/you/agentic-rag-flask  
2. py -m venv .venv  
3. call .venv\Scripts\activate.bat  
4. copy .env.example → .env and fill GEMINI_API_KEY  
5. pip install -r requirements.txt  
6. python ingest.py --refresh   (first-time vector build)  
7. waitress-serve --port 8000 "app:create_app()"  
8. Open http://localhost:8000 in your browser.

────────────────────────────────────────────────────────────
15. Future Enhancements
────────────────────────────────────────────────────────────
• Switch vector store to pgvector (PostgreSQL on Windows).  
• Add Windows-native speech synthesis via pyttsx3 (SAPI 5).  
• Package the whole app as a Windows Service using “nssm” or “pywin32 win32serviceutil”.  
• Electron or Tauri wrapper for a desktop edition.

════════════════════════════════════════════════════════════
With this Windows-native blueprint you can build, debug and deploy the Agentic RAG chatbot using nothing but a virtual-env and standard Windows tooling—no WSL, no Docker required. Happy coding!