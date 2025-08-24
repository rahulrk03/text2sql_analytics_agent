# text2sql_analytics_agent

> **Natural Language to SQL Analytics with Full-Stack Application (Backend API + Frontend Dashboard)**

Welcome! This project is a full-stack application that lets users query your PostgreSQL database using natural language. It features a FastAPI backend with AI-powered SQL generation and a modern Next.js frontend dashboard with TypeScript and Tailwind CSS.

---

## 🚀 Features
- **Full-Stack Architecture**: Separate backend (FastAPI) and frontend (Next.js) for scalable development
- **Natural Language to SQL**: Converts user questions into safe, read-only SQL using OpenAI (or AWS Bedrock) LLMs
- **Modern Frontend**: React/Next.js dashboard with TypeScript and Tailwind CSS for a polished user experience
- **Retrieval-Augmented Generation (RAG)**: Enriches queries with schema and business glossary hints for more accurate SQL
- **Streaming Responses**: Efficient streaming API for large query results with progressive JSON delivery
- **Robust Error Handling**: Comprehensive HTTP status codes (400, 422, 502, 503, 500) for different error scenarios
- **Serverless & Scalable**: Built on FastAPI, deployable to AWS Lambda via API Gateway using Mangum and Serverless Framework
- **Large Data Export**: Asynchronously export query results to S3 as CSV, with job status tracked in PostgreSQL and notifications via SQS
- **Secure by Design**: SQL safety checks, environment-based secrets, and IAM-ready for cloud best practices
- **Extensible**: Modular RAG pipeline, easy to swap LLM providers, and ready for semantic search or vector DB integration

---

## 🏗️ Architecture

### Backend (`/backend/`)
- **API**: FastAPI app (see `backend/app/api.py`) for query, export, and job status endpoints
- **RAG Layer**: Modular enrichment using schema and glossary (see `backend/shared/rag.py`)
- **LLM Integration**: OpenAI by default, but easily swappable for AWS Bedrock or others
- **Export Worker**: Lambda function (see `backend/lambda/export_worker.py`) processes export jobs, writes CSV to S3, and updates job status in PostgreSQL
- **AWS Services**: S3 (exports), SQS (job queue), Lambda (API & worker)
- **Database**: PostgreSQL for all analytics, job tracking, and status

### Frontend (`/frontend/`)
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript for type safety
- **Styling**: Tailwind CSS for modern, responsive design
- **Features**: Interactive dashboard for querying data, viewing results, and managing exports

---

## 🛠️ Quickstart

### Backend Setup

1. **Install Backend Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure Environment**
Set your environment variables (or use dotenv/SSM):
```bash
export AWS_REGION=ap-south-1
export DB_HOST=... DB_NAME=... DB_USER=... DB_PASS=...
export OPENAI_API_KEY=sk-...
```

3. **Deploy Backend to AWS**
```bash
cd backend
npm i -g serverless
sls deploy
```

### Frontend Setup

1. **Install Frontend Dependencies**
```bash
cd frontend
npm install
```

2. **Run Development Server**
```bash
npm run dev
```

3. **Build for Production**
```bash
npm run build
npm start
```

---

## 🔌 API Endpoints

The backend provides the following REST API endpoints:

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

### Backend Development
Run the FastAPI backend locally:
```bash
cd backend
uvicorn app.api:app --reload --port 8000
```

### Frontend Development
Run the Next.js frontend locally:
```bash
cd frontend
npm run dev
```

The frontend will be available at http://localhost:3000 and will attempt to connect to the backend at http://localhost:8000.

### Running Tests
The backend includes comprehensive unit tests for all API endpoints:
```bash
cd backend
# Run tests with pytest
python -m pytest tests/ -v

# Or use the test runner script
python run_tests.py
```

---

## 📝 Customization & Notes

### Backend Configuration
- **VPC/Private DB**: Use VPC config in `backend/serverless.yml` for private RDS
- **Secrets**: For production, store DB creds in AWS Secrets Manager or SSM
- **Large Exports**: For >10GB, use S3 multipart upload in the worker
- **Switch LLMs**: To use AWS Bedrock (Claude/Sonar/Titan), update the agent call in `backend/app/api.py` and set IAM permissions
- **Extend RAG**: Add semantic search, vector DB, or query history in `backend/shared/rag.py`

### Frontend Configuration
- **API Endpoint**: Update the API base URL in `frontend/src/app/page.tsx` to match your deployed backend
- **Styling**: Customize the Tailwind CSS configuration in `frontend/tailwind.config.ts`
- **Environment Variables**: Create `frontend/.env.local` for environment-specific configuration

---

## 📁 Project Structure

```
text2sql_analytics_agent/
├── backend/                    # FastAPI backend application
│   ├── app/                   # Main application code
│   │   └── api.py            # FastAPI routes and endpoints
│   ├── shared/               # Shared modules
│   │   ├── db.py            # Database connections and queries
│   │   ├── rag.py           # RAG pipeline and enrichment
│   │   ├── schema.py        # Database schema utilities
│   │   ├── security.py      # SQL safety and validation
│   │   └── glossary.py      # Business glossary for RAG
│   ├── lambda/              # AWS Lambda functions
│   │   └── export_worker.py # Background export processing
│   ├── tests/               # Backend test suite
│   ├── requirements.txt     # Python dependencies
│   ├── serverless.yml       # AWS deployment configuration
│   └── pytest.ini          # Test configuration
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   └── app/             # Next.js App Router
│   │       ├── layout.tsx   # Root layout component
│   │       ├── page.tsx     # Main dashboard page
│   │       └── globals.css  # Global styles
│   ├── public/              # Static assets
│   ├── package.json         # Node.js dependencies
│   ├── tailwind.config.ts   # Tailwind CSS configuration
│   └── tsconfig.json        # TypeScript configuration
├── README.md                # Project documentation
└── .gitignore              # Git ignore rules
```

---

## 🤝 Contributing & Feedback
Pull requests and suggestions are welcome! Feel free to open issues or reach out for improvements.

For development:
1. Backend changes: Work in the `/backend` directory and run tests with `pytest`
2. Frontend changes: Work in the `/frontend` directory and test with `npm run dev`
3. Ensure both backend and frontend builds pass before submitting PRs

---

## 📄 License
MIT License