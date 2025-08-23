# text2sql_analytics_agent

> **Natural Language to SQL Analytics API with RAG, Serverless, and Scalable Data Export**

Welcome! This project is a production-grade, serverless API that lets users query your PostgreSQL database using natural language. It leverages Retrieval-Augmented Generation (RAG) and LLMs to generate safe, read-only SQL, and supports exporting large query results to S3 with job tracking in PostgreSQL.

---

## 🚀 Features
- **Natural Language to SQL**: Converts user questions into safe, read-only SQL using OpenAI (or AWS Bedrock) LLMs.
- **Retrieval-Augmented Generation (RAG)**: Enriches queries with schema and business glossary hints for more accurate SQL.
- **Streaming Responses**: Efficient streaming API for large query results with progressive JSON delivery.
- **Robust Error Handling**: Comprehensive HTTP status codes (400, 422, 502, 503, 500) for different error scenarios.
- **Serverless & Scalable**: Built on FastAPI, deployable to AWS Lambda via API Gateway using Mangum and Serverless Framework.
- **Large Data Export**: Asynchronously export query results to S3 as CSV, with job status tracked in PostgreSQL and notifications via SQS.
- **Secure by Design**: SQL safety checks, environment-based secrets, and IAM-ready for cloud best practices.
- **Extensible**: Modular RAG pipeline, easy to swap LLM providers, and ready for semantic search or vector DB integration.

---

## 🏗️ Architecture
- **API**: FastAPI app (see `app/api.py`) for query, export, and job status endpoints.
- **RAG Layer**: Modular enrichment using schema and glossary (see `shared/rag.py`).
- **LLM Integration**: OpenAI by default, but easily swappable for AWS Bedrock or others.
- **Export Worker**: Lambda function (see `lambda/export_worker.py`) processes export jobs, writes CSV to S3, and updates job status in PostgreSQL.
- **AWS Services**: S3 (exports), SQS (job queue), Lambda (API & worker).
- **Database**: PostgreSQL for all analytics, job tracking, and status.

---

## 🛠️ Quickstart

### 1. Install Dependencies
```bash
npm i -g serverless
pip install -r requirements.txt
```

### 2. Configure Environment
Set your environment variables (or use dotenv/SSM):
```bash
export AWS_REGION=ap-south-1
export DB_HOST=... DB_NAME=... DB_USER=... DB_PASS=...
export OPENAI_API_KEY=sk-...
```

### 3. Deploy to AWS
```bash
sls deploy
```

### 4. API Endpoints
- `GET /health` — Health check
- `POST /query` — `{ question, page, page_size, stream }` → SQL + paginated results (streaming by default)
- `POST /export/start` — `{ question }` → `{ job_id }`
- `GET /export/status/{job_id}` — Get export job status & download link

**Query Endpoint Details:**
- `question` (string): Natural language question
- `page` (int, default=1): Page number for pagination
- `page_size` (int, default=50): Results per page
- `stream` (bool, default=true): Enable streaming response for better performance with large datasets

---

## 🧑‍💻 Local Development
Run locally with FastAPI & Uvicorn:
```bash
uvicorn app.api:app --reload --port 8000
```

---

## 📝 Customization & Notes
- **VPC/Private DB**: Use VPC config in `serverless.yml` for private RDS.
- **Secrets**: For production, store DB creds in AWS Secrets Manager or SSM.
- **Large Exports**: For >10GB, use S3 multipart upload in the worker.
- **Switch LLMs**: To use AWS Bedrock (Claude/Sonar/Titan), update the agent call in `app/api.py` and set IAM permissions.
- **Extend RAG**: Add semantic search, vector DB, or query history in `shared/rag.py`.

---

## 🤝 Contributing & Feedback
Pull requests and suggestions are welcome! Feel free to open issues or reach out for improvements.

---

## 📄 License
MIT License