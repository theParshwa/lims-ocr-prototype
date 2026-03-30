# LIMS OCR Document Processor

AI-powered system that extracts structured LIMS Load Sheet data from STP, PTP, and other laboratory documents (PDF/DOCX) and exports to Excel.

---

## Architecture

```
lims-ocr/
├── backend/                   # Python FastAPI backend
│   ├── ingestion/             # PDF, DOCX, OCR document parsing
│   ├── extraction/            # LangChain AI entity extraction pipeline
│   ├── mapping/               # Rule-based LIMS entity normalisation
│   │   └── config/            # Configurable mapping_rules.yaml
│   ├── validation/            # Schema + cross-reference validators
│   ├── excel_writer/          # openpyxl Excel generation
│   ├── api/                   # FastAPI routes (upload, jobs, export)
│   ├── models/                # Pydantic schemas + SQLAlchemy ORM
│   ├── logging_module/        # Structured audit logging (structlog)
│   └── tests/                 # pytest unit tests
├── frontend/                  # React + TypeScript + Tailwind frontend
│   └── src/
│       ├── components/        # Upload, Dashboard, DataPreview, Export
│       ├── services/          # API client (axios)
│       └── types/             # TypeScript types
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── nginx.conf
```

### Processing Pipeline

```
Upload → Ingest (PDF/DOCX/OCR) → Classify (LLM) → Extract Entities (LLM)
     → Apply Mapping Rules → Validate → Return JSON → User Edits
     → Generate Excel
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build |
| Tesseract | 5+ | OCR for scanned PDFs |
| Poppler | any | PDF-to-image conversion |
| Redis | 7+ | Background job queue (optional) |
| OpenAI key | — | AI extraction |

**Install Tesseract:**
- Windows: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract poppler`
- Ubuntu: `sudo apt install tesseract-ocr poppler-utils`

---

## Quick Start (Local Development)

### 1. Configure environment

```bash
cd backend
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

### 2. Install and run the backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Backend: http://localhost:8000
API docs: http://localhost:8000/docs

### 3. Install and run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

---

## Docker Deployment

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Fill in API keys

# 2. Build and start all services
docker-compose up --build

# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

---

## Configuration

### AI

Set in `backend/.env`:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

### Mapping Rules

Edit `backend/mapping/config/mapping_rules.yaml` to:
- Add new unit normalisations
- Add new analysis type keywords
- Configure which sheets apply to which document types

Example — add a new unit:
```yaml
unit_normalisation:
  "my custom unit": MY_UNIT_CODE
```

Example — add a new document type:
```yaml
document_type_sheets:
  MY_NEW_DOC_TYPE:
    - analysis
    - components
    - units
    - product_specs
```

---

## API Reference

### Upload Documents
```
POST /api/upload
Content-Type: multipart/form-data

files: [file1.pdf, file2.docx, ...]
```
Returns: `{ jobs: [{ job_id, filename, status }] }`

### Poll Job Status
```
GET /api/jobs/{job_id}
```
Returns: `{ job_id, status, document_type, result: ExtractionResult }`

Status flow: `pending → extracting → mapping → validating → complete`

### Update Extracted Data
```
PUT /api/jobs/{job_id}/data
Content-Type: application/json

{ ...ExtractionResult with user edits }
```

### Export to Excel
```
POST /api/jobs/{job_id}/export
```
Returns: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### List Jobs
```
GET /api/jobs?limit=50&offset=0
```

### Reprocess
```
POST /api/jobs/{job_id}/reprocess
```

### Delete
```
DELETE /api/jobs/{job_id}
```

---

## Excel Output Format

The generated Excel workbook contains these sheets (populated based on document type):

| Sheet | Description |
|-------|-------------|
| Summary | Document metadata and record counts |
| Analysis | Test methods / analytical procedures |
| Component | Individual parameters within each analysis |
| Units | Measurement unit definitions |
| Product | Products / materials under test |
| Product Grade | Quality grading definitions |
| Prod Grade Stage | Tests required per product/grade/stage |
| Product Spec | Acceptance limits (min/max/text) per product |
| T PH ITEM CODE | Pharmaceutical item codes |
| T PH ITEM CODE Spec | Spec assignments per item code |
| T PH ITEM CODE SUPP | Supplier data per item code |
| T PH SAMPLE PLAN | Sample collection plans |
| T PH SAMPLE PLAN Entry | Individual entries per sample plan |

**Cell highlighting:**
- Yellow = low confidence extraction (<60%)
- Red = validation error

---

## Running Tests

```bash
cd backend
# Activate venv first
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=html
```

---

## Confidence Scoring

Every extracted record carries a `confidence` score (0.0–1.0):

| Score | Level | Meaning |
|-------|-------|---------|
| ≥ 0.85 | High | AI is certain — direct mapping |
| 0.60–0.84 | Medium | Reasonable inference — review recommended |
| < 0.60 | Low | Ambiguous — **flagged yellow, requires human review** |

---

## Extending the System

### Add a new document type

1. Add recognition keywords to `extraction/prompts.py` → `CLASSIFIER_USER`
2. Add applicable sheets to `mapping/config/mapping_rules.yaml` under `document_type_sheets`
3. Add custom extraction prompt if the document has unique fields

### Add a new Excel sheet

1. Add Pydantic model to `models/schemas.py`
2. Add field to `ExtractionResult`
3. Add extraction logic to `extraction/entity_extractor.py`
4. Add sheet spec to `excel_writer/excel_generator.py` → `SHEET_SPECS`
5. Add sheet def to `frontend/src/components/DataPreview/sheetDefs.ts`

---

## Troubleshooting

**OCR not working:**
- Ensure Tesseract is installed and on PATH
- Windows: Set `tesseract_cmd` in `.env` or code
- Check `OCR_ENABLED=true` in `.env`

**LLM returning empty results:**
- Check API key is set correctly
- Ensure the document text is being extracted (check audit log)
- Try reducing `CHUNK_SIZE` for very long documents

**Large documents timing out:**
- Increase `proxy_read_timeout` in nginx.conf
- Reduce `CHUNK_SIZE` in `.env`

**Excel not downloading:**
- Check `outputs/` directory exists and is writable
- Verify job status is `complete` before exporting
