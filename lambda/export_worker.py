"""
Lambda worker for exporting query results to S3 as CSV and updating job status in DynamoDB.
"""

import csv
import os
import tempfile
import time
import traceback
import uuid

import boto3

from shared.db import get_psycopg_conn

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
EXPORT_BUCKET = os.getenv("EXPORT_BUCKET")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))

s3 = boto3.client("s3", region_name=AWS_REGION)


# --- Postgres job status helpers ---
def update_job_status(
    job_id, status, started_at=None, finished_at=None, row_count=None, error=None
):
    conn = get_psycopg_conn()
    cur = conn.cursor()
    sets = ["status = %s"]
    vals = [status]
    if started_at is not None:
        sets.append("started_at = %s")
        vals.append(started_at)
    if finished_at is not None:
        sets.append("finished_at = %s")
        vals.append(finished_at)
    if row_count is not None:
        sets.append("row_count = %s")
        vals.append(row_count)
    if error is not None:
        sets.append("error = %s")
        vals.append(error)
    vals.append(job_id)
    sql = f"UPDATE export_jobs SET {', '.join(sets)} WHERE job_id = %s"
    cur.execute(sql, vals)
    conn.commit()
    cur.close()
    conn.close()


def lambda_handler(event, context):
    """
    Lambda handler for processing export jobs from SQS, running SQL, and uploading CSV to S3.
    Args:
        event (dict): Lambda event payload from SQS.
        context: Lambda context object.
    """
    for rec in event.get("Records", []):
        attrs = rec["messageAttributes"]
        job_id = attrs["job_id"]["stringValue"]
        sql = attrs["sql"]["stringValue"]
        s3_key = attrs["s3_key"]["stringValue"]
        try:
            update_job_status(job_id, "IN_PROGRESS", started_at=int(time.time()))

            conn = get_psycopg_conn()
            cur = conn.cursor(name=f"export_cur_{uuid.uuid4().hex[:8]}")
            cur.itersize = BATCH_SIZE
            cur.execute(sql)
            cols = [d[0] for d in cur.description]

            tmp = os.path.join(tempfile.gettempdir(), f"{job_id}.csv")
            row_count = 0
            with open(tmp, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(cols)
                while True:
                    rows = cur.fetchmany(BATCH_SIZE)
                    if not rows:
                        break
                    row_count += len(rows)
                    w.writerows(rows)

            cur.close()
            conn.close()

            s3.upload_file(tmp, EXPORT_BUCKET, s3_key)
            os.remove(tmp)

            update_job_status(
                job_id, "SUCCESS", finished_at=int(time.time()), row_count=row_count
            )
        except Exception as e:
            update_job_status(
                job_id,
                "FAILED",
                finished_at=int(time.time()),
                error=f"{e.__class__.__name__}: {str(e)}\n{traceback.format_exc()[:1500]}",
            )
            raise
