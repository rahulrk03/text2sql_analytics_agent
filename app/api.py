"""
API module for the text2sql analytics agent.
This FastAPI app provides endpoints for querying a database using natural language,
exporting query results, and checking export job status. It integrates with OpenAI LLM,
AWS SQS, DynamoDB, and S3, and uses a glossary for RAG enrichment.
"""

import os
import time
import uuid

import boto3
from fastapi import FastAPI, HTTPException
from mangum import Mangum

# LLM (Agent)
from openai import OpenAI
from pydantic import BaseModel

from shared.db import get_conn, run_page
from shared.rag import build_prompt, enrich_query
from shared.schema import get_schema_text
from shared.security import extract_sql, is_safe

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# AWS config (defer resource creation for local dev)
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
EXPORT_BUCKET = os.getenv("EXPORT_BUCKET")
EXPORT_PREFIX = os.getenv("EXPORT_PREFIX", "exports")
SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME")


# --- Postgres job tracking helpers ---
def insert_job(job_id, s3_key):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO export_jobs (job_id, status, created_at, s3_key)
        VALUES (%s, %s, %s, %s)
        """,
        (job_id, "PENDING", int(time.time()), s3_key),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_job(job_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT job_id, status, s3_key, row_count, error FROM export_jobs WHERE job_id = %s
        """,
        (job_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "job_id": row[0],
        "status": row[1],
        "s3_key": row[2],
        "row_count": row[3],
        "error": row[4],
    }


def get_sqs():
    """Return an SQS client (created on demand)."""
    return boto3.client("sqs", region_name=AWS_REGION)


def get_s3():
    """Return an S3 client (created on demand)."""
    return boto3.client("s3", region_name=AWS_REGION)


_SQS_QUEUE_URL = None


def _queue_url():
    """
    Lazily fetch and cache the SQS queue URL for the export job queue.
    Returns:
        str: The SQS queue URL.
    """
    global _SQS_QUEUE_URL
    if _SQS_QUEUE_URL:
        return _SQS_QUEUE_URL
    sqs = get_sqs()
    r = sqs.get_queue_url(QueueName=SQS_QUEUE_NAME)
    _SQS_QUEUE_URL = r["QueueUrl"]
    return _SQS_QUEUE_URL


SYSTEM_PROMPT = (
    "You generate safe, read-only PostgreSQL. Return ONLY one SELECT between <sql></sql>. "
    "Use fully-qualified public.<table> names. No DDL/DML/COPY."
)


class QueryBody(BaseModel):
    """
    Request body for /query endpoint.
    Attributes:
        question (str): The user's natural language question.
        page (int): The page number for pagination.
        page_size (int): Number of rows per page.
    """

    question: str
    page: int = 1
    page_size: int = 50


class ExportBody(BaseModel):
    """
    Request body for /export/start endpoint.
    Attributes:
        question (str): The user's natural language question for export.
    """

    question: str


app = FastAPI(title="RAG + SQL Agent API (Serverless)")


@app.get("/health")
def health():
    """
    Health check endpoint.
    Returns:
        dict: Always {"ok": True}
    """
    return {"ok": True}


@app.post("/query")
def query(body: QueryBody):
    """
    Endpoint to answer a user's natural language question with a SQL query and paginated results.
    Args:
        body (QueryBody): The request body containing the question and pagination info.
    Returns:
        dict: The generated SQL, columns, rows, and pagination metadata.
    Raises:
        HTTPException: If LLM is not configured or SQL is unsafe/invalid.
    """
    if not client:
        raise HTTPException(status_code=500, detail="LLM not configured")

    schema = get_schema_text()
    enriched = enrich_query(body.question)
    prompt = build_prompt(body.question, schema, enriched)

    r = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    sql = extract_sql(r.choices[0].message.content or "")
    if not sql.lower().startswith("select") or not is_safe(sql):
        raise HTTPException(status_code=400, detail="Unsafe or invalid SQL generated")

    cols, rows, total = run_page(sql, body.page, body.page_size)
    return {
        "sql": sql,
        "columns": cols,
        "rows": rows,
        "pagination": {
            "page": body.page,
            "page_size": body.page_size,
            "total_rows": total,
            "total_pages": (total + body.page_size - 1) // body.page_size,
        },
    }


@app.post("/export/start")
def export_start(body: ExportBody):
    """
    Endpoint to start an export job for a user's question. Generates SQL, stores job in DynamoDB, and sends job to SQS.
    Args:
        body (ExportBody): The request body containing the question.
    Returns:
        dict: The job ID and status.
    Raises:
        HTTPException: If LLM is not configured or SQL is unsafe/invalid.
    """
    if not client:
        raise HTTPException(status_code=500, detail="LLM not configured")

    schema = get_schema_text()
    enriched = enrich_query(body.question)
    prompt = build_prompt(body.question, schema, enriched)
    r = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    sql = extract_sql(r.choices[0].message.content or "")
    if not sql.lower().startswith("select") or not is_safe(sql):
        raise HTTPException(status_code=400, detail="Unsafe or invalid SQL generated")

    job_id = str(uuid.uuid4())
    s3_key = f"{EXPORT_PREFIX}/{job_id}.csv"
    insert_job(job_id, s3_key)

    sqs = get_sqs()
    sqs.send_message(
        QueueUrl=_queue_url(),
        MessageBody="export_job",
        MessageAttributes={
            "job_id": {"StringValue": job_id, "DataType": "String"},
            "sql": {"StringValue": sql, "DataType": "String"},
            "s3_key": {"StringValue": s3_key, "DataType": "String"},
        },
    )
    return {"job_id": job_id, "status": "PENDING"}


@app.get("/export/status/{job_id}")
def export_status(job_id: str):
    """
    Endpoint to check the status of an export job.
    Args:
        job_id (str): The export job ID.
    Returns:
        dict: The job status, and if successful, a download URL and row count.
    Raises:
        HTTPException: If the job is not found.
    """
    item = get_job(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="job not found")

    status = item["status"]
    if status == "SUCCESS":
        s3 = get_s3()
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": os.getenv("EXPORT_BUCKET"), "Key": item["s3_key"]},
            ExpiresIn=3600,
        )
        return {
            "job_id": job_id,
            "status": status,
            "download_url": url,
            "row_count": item["row_count"] or 0,
        }
    elif status == "FAILED":
        return {
            "job_id": job_id,
            "status": status,
            "error": item["error"] or "unknown",
        }
    return {"job_id": job_id, "status": status}


handler = Mangum(app)
"""
AWS Lambda handler for the FastAPI app using Mangum adapter.
"""
