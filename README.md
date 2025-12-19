## ML Products Grouping

This application groups equivalent products from vendor CSV files, even when fields differ (different headers, missing columns, name/brand variations, etc.).

The workflow consists of two steps:
1. **Import products** from CSV files - maps CSV headers to a standard schema using LLM, creates products with embeddings
2. **Group products** - clusters product embeddings to identify equivalent products

---

## Data model

Core tables:

- **`vendors`** - vendor information
- **`files`** - uploaded CSV files
- **`products`** - product data with embeddings (pgvector)
- **`product_processing`** - tracks CSV import status
- **`group_processing`** - tracks grouping status
- **`groups`** - product groups created by clustering
- **`product_brands`**, **`product_categories`** - normalized brand and category data

---

## API routes

- `GET /health/` — service health
- `GET /health/db` — database connectivity check

- `POST /vendors/` — create vendor
- `GET /vendors/` — list vendors
- `GET /vendors/{vendor_id}` — get vendor

- `POST /files/start-upload` — create file record and get presigned upload URL
- `POST /files/complete-upload/{file_id}` — mark file as uploaded
- `GET /files/` — list files
- `GET /files/{file_id}` — get file

- `POST /products/import-from-csv` — import products from CSV (background task)
- `GET /products/processing/{product_processing_id}` — check import status

- `POST /groups/group` — group vendor products (background task)
- `GET /groups/processing/{group_processing_id}` — check grouping status
- `GET /groups/` — get grouped products (requires `group_processing_id` query param)

---

## Workflow

### 1) Create a vendor

```bash
curl -sS -X POST "http://localhost:8000/vendors/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Vendor A"}'
```

### 2) Upload CSV file

Start upload and get presigned URL:

```bash
curl -sS -X POST "http://localhost:8000/files/start-upload" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"vendor_a.csv"}'
```

Upload file using the presigned URL:

```bash
curl -sS -X PUT "<PRESIGNED_URL>" \
  -H "Content-Type: text/csv" \
  --data-binary "@media/vendor_a.csv"
```

Complete upload:

```bash
curl -sS -X POST "http://localhost:8000/files/complete-upload/<FILE_ID>"
```

### 3) Import products from CSV

```bash
curl -sS -X POST "http://localhost:8000/products/import-from-csv" \
  -H "Content-Type: application/json" \
  -d '{"file_id": <FILE_ID>, "vendor_id": <VENDOR_ID>}'
```

Check import status:

```bash
curl -sS "http://localhost:8000/products/processing/<PRODUCT_PROCESSING_ID>"
```

### 4) Group products

```bash
curl -sS -X POST "http://localhost:8000/groups/group" \
  -H "Content-Type: application/json" \
  -d '{"file_id": <FILE_ID>, "vendor_id": <VENDOR_ID>}'
```

Check grouping status:

```bash
curl -sS "http://localhost:8000/groups/processing/<GROUP_PROCESSING_ID>"
```

### 5) Fetch grouped products

```bash
curl -sS "http://localhost:8000/groups/?group_processing_id=<GROUP_PROCESSING_ID>"
```

---

## Background processing

### Import products from CSV (`import_products_from_csv_task`)

1. Downloads CSV from storage
2. Maps CSV headers to standard schema using LLM
3. Creates products with brand/category normalization
4. Generates embeddings for each product
5. Updates `ProductProcessing` status: `pending` → `processing` → `completed` (or `failed`)

### Group products (`group_vendor_products_task`)

1. Loads all products for the vendor (with embeddings)
2. Clusters product embeddings using HDBSCAN
3. Creates groups and assigns products to groups
4. Updates `GroupProcessing` status: `pending` → `processing` → `completed` (or `failed`)

---

## Configuration

Required environment variables (see `src/config.py`):

- `OPENAI_API_KEY` - OpenAI API key
- `POSTGRES_URI` - PostgreSQL connection string (async, e.g. `postgresql+asyncpg://...`)
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_ENDPOINT_URL`, `MINIO_AWS_BUCKET_NAME`, `MINIO_AWS_REGION` - MinIO/S3 configuration
- `LOCALSTACK_AWS_ACCESS_KEY_ID`, `LOCALSTACK_AWS_SECRET_ACCESS_KEY`, `LOCALSTACK_AWS_REGION`, `LOCALSTACK_AWS_ENDPOINT_URL` - LocalStack configuration
- `SQS_QUEUE_NAME`, `SQS_QUEUE_URL`, `CELERY_BROKER_URL` - Celery/SQS configuration
- `AI_MODEL` (default: `gpt-4o-mini`)
- `EMBEDDING_MODEL` (default: `text-embedding-3-small`)
- `EMBEDDING_DIMENSION` (default: `1536`)

---

## Local development

### Prerequisites

- Python 3.12+
- `uv` package manager
- Docker + Docker Compose

### Setup

1. Install dependencies: `make setup-project`
2. Start infrastructure: `make up` (runs migrations automatically)
3. Run API: `uv run uvicorn src.app:app --reload --host 0.0.0.0 --port 8000`
4. Run worker: `uv run celery -A src.celery_app.app worker --loglevel=INFO`

API docs: `http://localhost:8000/docs`
