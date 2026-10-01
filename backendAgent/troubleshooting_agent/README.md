# troubleshooting_agent

An enterprise **Google Agent Development Kit (ADK)** application using **BigQuery Vector Search** as a RAG (Retrieval-Augmented Generation) backend.

The agent handles two core operational workflows:
1. **User RAG Retrieval:** Diagnoses cloud error messages and pipeline failures by performing cosine similarity vector searches against BigQuery knowledge base entries.
2. **Admin Knowledge Ingestion:** Accepts unstructured raw text from administrators, dynamically inspects current BigQuery table columns, extracts values matching those columns via Gemini, and inserts the record with auto-generated embeddings via BigQuery ML (`text-embedding-005`).

---

## Architecture

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
BigQuery Configuration Summary
Resource	Value / Path
GCP Project	saas-poc-env
Location / Region	US
BigQuery Dataset	saas-poc-env.support_rag
Knowledge Base Table	saas-poc-env.support_rag.knowledge_base
Cloud Resource Connection	saas-poc-env.US.vertex_conn
Remote Embedding Model	saas-poc-env.support_rag.embedding_model
Embedding Endpoint	text-embedding-005 (768 dimensions)
Vector Index	kb_vector_idx (COSINE distance, IVF index)
Step-by-Step Google Cloud & BigQuery Setup
Step 1: Authenticate and Set GCP Project
gcloud auth application-default login
gcloud config set project saas-poc-env
Step 2: Enable Required GCP APIs
gcloud services enable \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  aiplatform.googleapis.com
Step 3: Create Cloud Resource Connection
bq mk --connection \
  --location=US \
  --project_id=saas-poc-env \
  --connection_type=CLOUD_RESOURCE \
  vertex_conn
Step 4: Grant Vertex AI Permissions to Connection Service Account
Retrieve the service account associated with the connection:

bq show --location=US --connection vertex_conn
Grant roles/aiplatform.user with --condition=None to ensure unconditional permanent access:

gcloud projects add-iam-policy-binding saas-poc-env \
  --member="serviceAccount:bqcx-736134210043-h7yb@gcp-sa-bigquery-condel.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" \
  --condition=None
Step 5: Initialize BigQuery Objects (DDL)
Run the following SQL in the BigQuery console for saas-poc-env:

-- 1. Create Dataset
CREATE SCHEMA IF NOT EXISTS `saas-poc-env.support_rag`
OPTIONS (location = 'US');

-- 2. Create Remote Embedding Model
CREATE OR REPLACE MODEL `saas-poc-env.support_rag.embedding_model`
REMOTE WITH CONNECTION `saas-poc-env.US.vertex_conn`
OPTIONS (ENDPOINT = 'text-embedding-005');

-- 3. Create Knowledge Base Table
CREATE TABLE IF NOT EXISTS `saas-poc-env.support_rag.knowledge_base` (
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
ON `saas-poc-env.support_rag.knowledge_base`(embedding)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF');
Installation & Environment Configuration
Navigate to backend directory:

cd backendAgent
Activate your virtual environment:

source .agent/bin/activate
Install dependencies:

pip install -r troubleshooting_agent/requirements.txt
Verify .env configuration:
Ensure backendAgent/.env has:

GOOGLE_CLOUD_PROJECT=saas-poc-env
GOOGLE_CLOUD_REGION=US
BQ_DATASET_ID=support_rag
BQ_TABLE_ID=knowledge_base
BQ_EMBEDDING_MODEL_ID=embedding_model
GEMINI_MODEL=gemini-2.5-flash
TOP_K_RESULTS=3
LOG_LEVEL=INFO
How Vector Ingestion Works
Via the Agent (Admin Text Ingestion):
When an admin submits unstructured text, the ingest_kb_record tool calls ML.GENERATE_EMBEDDING in the INSERT query. Embeddings are automatically computed and saved into the embedding column.
Direct SQL Insert:
Always wrap inserts with ML.GENERATE_EMBEDDING:
INSERT INTO `saas-poc-env.support_rag.knowledge_base` (
  kb_id, error_symptom, probable_cause, impacted_phase, step_by_step_resolution, search_content, embedding
)
SELECT
  kb_id, error_symptom, probable_cause, impacted_phase, step_by_step_resolution, search_content,
  ml_generate_embedding_result AS embedding
FROM ML.GENERATE_EMBEDDING(
  MODEL `saas-poc-env.support_rag.embedding_model`,
  (...)
);
Running the Agent
Option 1: ADK Web Server (Browser UI)
adk web --allow_origins="regex:.*"
Navigate to the URL printed in the terminal (default: http://localhost:8000).

Option 2: ADK CLI (Interactive Terminal Chat)
adk run troubleshooting_agent
Option 3: Standalone Test Runner Script
python -m troubleshooting_agent.run_agent
Sample Queries
1. User Retrieval (Semantic Match)
"Our deployment failed with 403 PERMISSION_DENIED: Caller does not have required IAM permissions. How do I resolve this?"
"We are hitting persistent disk limits and quota exceeded errors during scale-out."
"A rollback was triggered due to circuit breaker trip during rolling upgrade."
2. Admin Ingestion (Dynamic Parsing & Vectorization)
Please add this record to the knowledge base:

KB-ALM-009
NETWORK_PEERING_FAILED: Subnet collision
Overlapping CIDR blocks detected between primary VPC and secondary service VPC.
Network Setup
1. Inspect IP CIDR ranges in VPC Network details.
2. Allocate a non-overlapping /24 block for the peer network.
3. Re-initiate peering connection.
