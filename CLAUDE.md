# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
# Activate venv first (Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate)

# Run dev server
uvicorn api.main:app --reload --port 8000

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_ingestion.py -v

# Run a single test
pytest tests/test_ingestion.py::TestPDFExtractor::test_raises_on_missing_file -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html
```

### Frontend

```bash
cd frontend
npm run dev      # dev server on http://localhost:3000
npm run build    # tsc + vite build
npm run lint     # ESLint (zero warnings tolerance)
```

## Architecture

### Processing Flow

```
POST /api/upload
  → saves file to disk, creates LIMSJob in SQLite, starts BackgroundTask
  → _process_document (async background)
      → RAG retrieval (retrieve_similar) for training context
      → ExtractionPipeline.run() in thread pool executor
          → ingestion/dispatcher.py  — routes .pdf → PDFExtractor, .docx → DOCXExtractor
          → DocumentClassifier       — LLM call to detect doc type (STP/PTP/SPEC/METHOD/SOP/OTHER)
          → EntityExtractor          — chunked LLM extraction, one JSON call per chunk
          → LIMSMapper               — applies mapping_rules.yaml (unit normalisation, analysis types)
          → SchemaValidator + CrossRefValidator
      → job.set_result(result.model_dump()) → persisted in SQLite as JSON blob
```

Non-LIMS documents are rejected at the classifier stage (DocumentType.OTHER) and the job is marked FAILED with an explanatory message.

### Key Abstractions

- **`ExtractionResult`** ([backend/models/schemas.py](backend/models/schemas.py)) — root output object; holds lists of typed records for all 30 LIMS sheets. All sheet keys are in `SHEET_KEYS`.
- **`_Annotated` mixin** — every record model inherits `confidence`, `confidence_level`, `review_notes`, `source_text`. These are stripped before Excel export.
- **`EntityExtractor`** ([backend/extraction/entity_extractor.py](backend/extraction/entity_extractor.py)) — splits document text into chunks (default 12 000 chars / 200 overlap), calls OpenAI with `response_format: json_schema` (strict mode) once per chunk, merges results across chunks.
- **`get_llm()`** ([backend/extraction/llm_factory.py](backend/extraction/llm_factory.py)) — `@lru_cache` singleton; returns `ChatOpenAI` configured from `settings`.
- **`LIMSJob`** ([backend/models/lims_models.py](backend/models/lims_models.py)) — SQLAlchemy ORM model; `result` column is a JSON blob of the full `ExtractionResult`.

### Frontend Data Flow

- React Query polls `GET /api/jobs/{job_id}` for status updates during extraction.
- `DataPreview` renders all 30 sheets using AG Grid (`themeQuartz`). Column definitions live in [frontend/src/components/DataPreview/sheetDefs.ts](frontend/src/components/DataPreview/sheetDefs.ts) — one `SheetDef` entry per sheet.
- Vite proxies all `/api` requests to `http://localhost:8000` (no CORS issues in dev). Frontend dev port is **3000** (not 5173).

### Configuration

All backend settings are in [backend/config.py](backend/config.py) via `pydantic-settings` and loaded from `backend/.env`. Key env vars: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o`), `OCR_ENABLED`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `DATABASE_URL` (defaults to SQLite).

### Extending

**Add a new LIMS sheet:**
1. Add Pydantic model to [backend/models/schemas.py](backend/models/schemas.py) (extend `_Annotated`)
2. Add key to `SHEET_KEYS` list and field to `ExtractionResult`
3. Add extraction logic to [backend/extraction/entity_extractor.py](backend/extraction/entity_extractor.py)
4. Add sheet spec to [backend/excel_writer/excel_generator.py](backend/excel_writer/excel_generator.py) → `SHEET_SPECS`
5. Add `SheetDef` entry to [frontend/src/components/DataPreview/sheetDefs.ts](frontend/src/components/DataPreview/sheetDefs.ts)

**Add a new document type:**
1. Add recognition keywords to [backend/extraction/prompts.py](backend/extraction/prompts.py) → `CLASSIFIER_USER`
2. Add applicable sheets under `document_type_sheets` in [backend/mapping/config/mapping_rules.yaml](backend/mapping/config/mapping_rules.yaml)

**Add unit normalisations or analysis type keywords:** edit [backend/mapping/config/mapping_rules.yaml](backend/mapping/config/mapping_rules.yaml) only — no code changes needed.
