## ML Products Grouping — Technical Documentation

This project groups “equivalent” products from vendor CSV files even when fields differ (different headers, missing columns, name/brand variations, etc.). It uses:

- **FastAPI** for the HTTP API
- **PostgreSQL + pgvector** for persistence + embedding storage
- **MinIO (S3-compatible)** for CSV storage and presigned uploads/downloads
- **Celery + SQS (LocalStack in dev)** for background processing
- **OpenAI (via LangChain)** for:
  - CSV header → schema mapping (structured output)
  - product text embeddings
- **HDBSCAN** for clustering product embeddings into groups

---

## Architecture (high level)

- **API service** (`src/app.py`)
  - Stores a SQLAlchemy **AsyncEngine** on `app.state.engine`
  - Exposes endpoints to upload files, create vendors, start grouping, and query results
- **Worker** (`src/tasks.py`, `src/celery_app.py`)
  - Celery task `process_vendor_file_task(file_processing_id, vendor_id)` runs the full pipeline:
    - download CSV from MinIO
    - ask LLM to map CSV headers to a standard schema
    - create new `products` + embeddings
    - cluster embeddings into groups
    - persist `groups` and set `products.group_id`
  - Celery task `regroup_vendor_products_task(file_processing_id, vendor_id)` re-runs clustering for an existing vendor:
    - loads vendor products already in the DB
    - clusters embeddings into new groups
    - persists new `groups` and updates `products.group_id`
- **Infra (dev)** (`docker-compose-dev.yml`)
  - `db`: `pgvector/pgvector:pg16`
  - `aws`: `localstack/localstack` (SQS)
  - `minio`: object storage
  - `createbucket`: creates the bucket on startup

---

## Data model (SQLAlchemy)

Core tables (see `src/db/models/`):

- **`vendors`** (`Vendor`)
  - `id`, `name`
- **`files`** (`File`)
  - `id`, `file_name`, `extension`, `key`, `uploaded_at`
- **`file_processing`** (`FileProcessing`)
  - `id`, `file_id`, `vendor_id`, `status` (`pending|processing|completed|failed`)
- **`products`** (`Product`)
  - `id`, `sku` (unique), `name`, `description`, `price`
  - `vendor_id`
  - `brand_id`, `category_id`
  - `embedding` (pgvector `VECTOR(dim=EMBEDDING_DIMENSION)`)
  - `group_id`
- **`groups`** (`Group`)
  - `id`, `vendor_id`, `file_processing_id`
- **`product_brands`**, **`product_categories`**
  - stored with `name` and `normalized_name`

All models inherit from `Base` (see `src/db/models/base.py`) which provides:

- `id` (PK)
- `created_at`, `updated_at` (server-side timestamps)

---

## API routes (mounted routers)

Routers are mounted in `src/app.py`:

- `GET /health/` — service health
- `GET /health/db` — checks DB connectivity (`SELECT 1`)

- `POST /vendors/` — create vendor
- `GET /vendors/` — list vendors
- `GET /vendors/{vendor_id}` — get vendor

- `POST /files/start-upload` — create `File` row + return a presigned **PUT** URL
- `POST /files/complete-upload/{file_id}` — mark `uploaded_at` on the file
- `GET /files/` — list files
- `GET /files/{file_id}` — get file

- `POST /groups/` — create `file_processing` row and enqueue the Celery task
- `POST /groups/regroup` — create `file_processing` row and enqueue the regroup Celery task
- `GET /groups/check-status/{file_processing_id}` — read processing status
- `GET /groups/{vendor_id}` — list grouped products for a vendor

Notes:

- The repository contains `src/routes/products.py`, but it is **not currently mounted** in `src/app.py`.

---

## End-to-end workflow (upload → group → fetch results)

### 1) Create a vendor

```bash
curl -sS -X POST "http://localhost:8000/vendors/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Vendor A"}'
```

### 2) Start an upload (presigned URL)

```bash
curl -sS -X POST "http://localhost:8000/files/start-upload" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"vendor_a.csv"}'
```

Response contains `url` (presigned PUT), `file_id`, and the generated S3 `key`.

### 3) Upload the CSV to MinIO using the presigned URL

```bash
curl -sS -X PUT "<PRESIGNED_URL_FROM_STEP_2>" \
  -H "Content-Type: text/csv" \
  --data-binary "@media/vendor_a.csv"
```

### 4) Complete the upload (marks the file as uploaded)

```bash
curl -sS -X POST "http://localhost:8000/files/complete-upload/<FILE_ID>"
```

### 5) Start grouping (creates `file_processing` and enqueues background job)

```bash
curl -sS -X POST "http://localhost:8000/groups/" \
  -H "Content-Type: application/json" \
  -d '{"file_id": <FILE_ID>, "vendor_id": <VENDOR_ID>}'
```

### 5b) Regroup (recluster existing vendor products without re-ingesting CSV)

Use this if products for the vendor already exist in the DB and you want to re-run clustering (e.g. after tuning clustering settings or after incremental changes to product data).

Note: the request still requires a `file_id` to create a `file_processing` record for traceability, but the regroup pipeline does **not** re-download or re-parse the CSV. Use the latest uploaded `file_id` for that vendor (or any valid file belonging to the vendor).

```bash
curl -sS -X POST "http://localhost:8000/groups/regroup" \
  -H "Content-Type: application/json" \
  -d '{"file_id": <FILE_ID>, "vendor_id": <VENDOR_ID>}'
```

### 6) Poll status

```bash
curl -sS "http://localhost:8000/groups/check-status/<FILE_PROCESSING_ID>"
```

### 7) Fetch grouped products

```bash
curl -sS "http://localhost:8000/groups/<VENDOR_ID>"
```

---

## Background processing pipeline (what the worker does)

Implemented in `src/vendor/services/processing.py`:

- **Status management (both tasks)**
  - `pending` → `processing` → `completed` (or `failed`)

### Full ingest + grouping (`process_vendor_file_task` → `process_vendor_file`)

- **CSV download**
  - uses MinIO presigned **GET** URL and streams to a temp file (`src/services/file.py`)
- **Header mapping via LLM**
  - reads CSV headers + a few sample rows
  - asks the LLM (structured output) to map vendor headers → target schema (`src/vendor/services/csv_processing.py`)
- **Product creation**
  - creates `ProductBrand` / `ProductCategory` (when needed)
  - creates `Product` rows
  - generates embeddings via `OpenAIEmbeddings.aembed_query(...)` (`src/vendor/services/product.py`)
- **Clustering**
  - clusters embeddings with HDBSCAN (`src/vendor/ai/cluster.py`)
- **Persist groups**
  - creates a `Group` per cluster and sets `products.group_id` for each cluster’s products

### Regroup existing products (`regroup_vendor_products_task` → `regroup_vendor_products`)

- **Load existing products**
  - fetches all products for the vendor from the DB (expects embeddings to already exist)
- **Clustering + persist groups**
  - clusters embeddings with HDBSCAN and persists new `groups`, updating `products.group_id`

---

## Configuration (environment variables)

All required variables are defined in `src/config.py` (Pydantic settings; reads from `.env`):

- **OpenAI**
  - `OPENAI_API_KEY`
  - `AI_MODEL` (default `gpt-4o-mini`)
  - `EMBEDDING_MODEL` (default `text-embedding-3-small`)
  - `EMBEDDING_DIMENSION` (default `1536`)
- **Database**
  - `POSTGRES_URI` (must be async SQLAlchemy DSN, e.g. `postgresql+asyncpg://...`)
- **LocalStack (SQS)**
  - `LOCALSTACK_AWS_ACCESS_KEY_ID`
  - `LOCALSTACK_AWS_SECRET_ACCESS_KEY`
  - `LOCALSTACK_AWS_REGION`
  - `LOCALSTACK_AWS_ENDPOINT_URL`
- **MinIO (S3-compatible)**
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_ENDPOINT_URL`
  - `MINIO_AWS_BUCKET_NAME`
  - `MINIO_AWS_REGION`
- **Celery / SQS**
  - `SQS_QUEUE_NAME`
  - `SQS_QUEUE_URL`
  - `CELERY_BROKER_URL`

### Example `.env` (dev)

Note: your `.env` is intentionally not committed. Create one locally with **all** required keys (Pydantic settings uses `extra=forbid`).

```bash
# OpenAI
OPENAI_API_KEY=replace-me
AI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Postgres (dev docker-compose)
POSTGRES_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres

# LocalStack (SQS) (dev docker-compose)
LOCALSTACK_AWS_ACCESS_KEY_ID=test
LOCALSTACK_AWS_SECRET_ACCESS_KEY=test
LOCALSTACK_AWS_REGION=us-east-1
LOCALSTACK_AWS_ENDPOINT_URL=http://localhost:4566

# MinIO (S3-compatible) (dev docker-compose)
MINIO_ACCESS_KEY=miniouser
MINIO_SECRET_KEY=miniopassword
MINIO_ENDPOINT_URL=http://localhost:9000
MINIO_AWS_BUCKET_NAME=uploads
MINIO_AWS_REGION=us-east-1

# Celery / SQS
SQS_QUEUE_NAME=ml-products-grouping
# After running `make up` (which runs `script.py`), set this to the printed QueueUrl
SQS_QUEUE_URL=http://localhost:4566/000000000000/ml-products-grouping
# Celery SQS transport (credentials come from LocalStack envs above)
CELERY_BROKER_URL=sqs://
```

---

## Local development (quickstart)

### Prereqs

- Python **3.12+**
- `uv` installed (`https://github.com/astral-sh/uv`)
- Docker + Docker Compose

### 1) Install Python dependencies

```bash
make setup-project
```

### 2) Start infra (Postgres + LocalStack + MinIO)

```bash
make up
```

`make up` will also run `script.py`, which waits for LocalStack and creates the SQS queue.

### 3) Run database migrations

```bash
uv run alembic upgrade head
```

### 4) Run the API

```bash
uv run uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### 5) Run the worker

In another terminal:

```bash
uv run celery -A src.celery_app.app worker --loglevel=INFO
```

---

## Repo pointers

- **App entrypoint**: `src/app.py`
- **Routers**: `src/routes/`
- **Celery worker / tasks**: `src/celery_app.py`, `src/tasks.py`
- **Vendor processing pipeline**: `src/vendor/services/processing.py`
- **DB models**: `src/db/models/`
- **Migrations**: `alembic/`
- **Dev infra**: `docker-compose-dev.yml`
