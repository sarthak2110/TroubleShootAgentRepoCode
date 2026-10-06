
---

# troubleshooting_agent

An enterprise **Google Agent Development Kit (ADK)** application using **BigQuery Vector Search** as a RAG (Retrieval-Augmented Generation) backend.

The agent handles two core operational workflows:
1. **User RAG Retrieval:** Diagnoses cloud error messages and pipeline failures by performing cosine similarity vector searches against BigQuery knowledge base entries.
2. **Admin Knowledge Ingestion:** Accepts unstructured raw text from administrators, dynamically inspects current BigQuery table columns, extracts values matching those columns via Gemini, and inserts the record with auto-generated embeddings via BigQuery ML (`text-embedding-005`).

---

## Architecture

```
                       User Prompt / Admin Text
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │   troubleshooting_agent   │
                    │        (Google ADK)       │
                    └─────────────┬─────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
      [query_knowledge_base]             [ingest_kb_record]
                 │                                 │
                 │                                 ├─► Inspect BQ Columns (Dynamic)
                 │                                 ├─► Gemini Field Extraction
                 │ VECTOR_SEARCH                   ▼
                 │                      ML.GENERATE_EMBEDDING
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                   ┌───────────────────────────────┐
                   │    Google BigQuery (RAG)      │
                   │  - Dataset: support_rag       │
                   │  - Table: knowledge_base      │
                   │  - Vector Index: COSINE (IVF) │
                   └───────────────────────────────┘
```

---

## Directory Structure

```text
backendAgent/
├── .env                              # Environment variables
└── troubleshooting_agent/
    ├── __init__.py                   # Package exports (root_agent)
    ├── agent.py                      # Root ADK agent configuration
    ├── config.py                     # Central configuration & logging
    ├── run_agent.py                  # Standalone test runner
    ├── requirements.txt              # Project dependencies
    ├── README.md                     # Documentation
    ├── services/
    │   ├── __init__.py
    │   └── bigquery_service.py       # Dynamic DDL, Vector Search & parameterized insert
    └── tools/
        ├── __init__.py
        ├── ingest_tool.py            # Dynamic schema parsing & ingestion tool
        └── query_tool.py             # BigQuery vector search tool
```

---

## BigQuery Configuration Summary

| Resource | Value / Pattern |
|---|---|
| **Location / Region** | `US` |
| **BigQuery Dataset** | `<PROJECT_ID>.support_rag` |
| **Knowledge Base Table** | `<PROJECT_ID>.support_rag.knowledge_base` |
| **Cloud Resource Connection** | `<PROJECT_ID>.US.<CONNECTION_NAME>` |
| **Remote Embedding Model** | `<PROJECT_ID>.support_rag.<EMBEDDING_MODEL_NAME>` |
| **Embedding Endpoint** | `text-embedding-005` (768 dimensions) |
| **Vector Index** | `kb_vector_idx` (COSINE distance, IVF index) |

---

## Step-by-Step Google Cloud & BigQuery Setup

### Step 1: Authenticate and Set GCP Project
```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

### Step 2: Enable Required GCP APIs
```bash
gcloud services enable \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  aiplatform.googleapis.com
```

### Step 3: Create Cloud Resource Connection
```bash
bq mk --connection \
  --location=US \
  --project_id=<PROJECT_ID> \
  --connection_type=CLOUD_RESOURCE \
  vertex_conn
```

### Step 4: Grant Vertex AI Permissions to Connection Service Account
Retrieve the service account associated with the connection:
```bash
bq show --location=US --connection vertex_conn
```

Look for `serviceAccountId` in the output, then grant `roles/aiplatform.user` with `--condition=None` to ensure unconditional permanent access:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<CONNECTION_SERVICE_ACCOUNT_EMAIL>" \
  --role="roles/aiplatform.user" \
  --condition=None
```

### Step 5: Initialize BigQuery Objects (DDL)
Run the following SQL in the BigQuery console (replace `<PROJECT_ID>` with your project ID):

```sql
-- 1. Create Dataset
CREATE SCHEMA IF NOT EXISTS `<PROJECT_ID>.support_rag`
OPTIONS (location = 'US');

-- 2. Create Remote Embedding Model
CREATE OR REPLACE MODEL `<PROJECT_ID>.support_rag.embedding_model`
REMOTE WITH CONNECTION `<PROJECT_ID>.US.vertex_conn`
OPTIONS (ENDPOINT = 'text-embedding-005');

-- 3. Create Knowledge Base Table
CREATE TABLE IF NOT EXISTS `<PROJECT_ID>.support_rag.knowledge_base` (
  kb_id STRING NOT NULL,
  error_symptom STRING NOT NULL,
  probable_cause STRING,
  impacted_phase STRING,
  step_by_step_resolution STRING,
  search_content STRING,
  embedding ARRAY<FLOAT64>
);

-- 4. Create Cosine Vector Search Index
CREATE VECTOR INDEX IF NOT EXISTS kb_vector_idx
ON `<PROJECT_ID>.support_rag.knowledge_base`(embedding)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF');
```

---

## Installation & Environment Configuration

1. **Navigate to the backend directory:**
   ```bash
   cd backendAgent
   ```

2. **Activate your virtual environment:**
   ```bash
   source .agent/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r troubleshooting_agent/requirements.txt
   ```

4. **Verify `.env` configuration:**
   Ensure `backendAgent/.env` has:
   ```bash
   GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
   GOOGLE_CLOUD_REGION=US
   BQ_DATASET_ID=support_rag
   BQ_TABLE_ID=knowledge_base
   BQ_EMBEDDING_MODEL_ID=embedding_model
   GEMINI_MODEL=gemini-2.5-flash
   TOP_K_RESULTS=3
   LOG_LEVEL=INFO
   ```

---

## How Vector Ingestion Works

- **Via the Agent (Admin Text Ingestion):**
  When an admin submits unstructured text, the `ingest_kb_record` tool calls `ML.GENERATE_EMBEDDING` in the `INSERT` query. Embeddings are **automatically computed and saved** into the `embedding` column.
- **Direct SQL Insert:**
  Always wrap inserts with `ML.GENERATE_EMBEDDING`:
  ```sql
  INSERT INTO `<PROJECT_ID>.support_rag.knowledge_base` (
    kb_id, error_symptom, probable_cause, impacted_phase, step_by_step_resolution, search_content, embedding
  )
  SELECT
    kb_id, error_symptom, probable_cause, impacted_phase, step_by_step_resolution, search_content,
    ml_generate_embedding_result AS embedding
  FROM ML.GENERATE_EMBEDDING(
    MODEL `<PROJECT_ID>.support_rag.embedding_model`,
    (...)
  );
  ```

---

## Running the Agent

### Option 1: ADK Web Server (Browser UI)
```bash
adk web --allow_origins="regex:.*"
```
Navigate to the URL printed in the terminal (default: `http://localhost:8000`).

### Option 2: ADK CLI (Interactive Terminal Chat)
```bash
adk run troubleshooting_agent
```

### Option 3: Standalone Test Runner Script
```bash
python -m troubleshooting_agent.run_agent
```

### Option 4: Agent Engine Deployement
```bash
python -m deployment.deploy
```

---

## Sample Queries

### 1. User Retrieval (Semantic Match)
- *"Our deployment failed with `403 PERMISSION_DENIED: Caller does not have required IAM permissions`. How do I resolve this?"*
- *"We are hitting persistent disk limits and quota exceeded errors during scale-out."*
- *"A rollback was triggered due to circuit breaker trip during rolling upgrade."*

### 2. Admin Ingestion (Dynamic Parsing & Vectorization)
```text
Please add this record to the knowledge base:

KB-ALM-009
NETWORK_PEERING_FAILED: Subnet collision
Overlapping CIDR blocks detected between primary VPC and secondary service VPC.
Network Setup
1. Inspect IP CIDR ranges in VPC Network details.
2. Allocate a non-overlapping /24 block for the peer network.
3. Re-initiate peering connection.
```

```