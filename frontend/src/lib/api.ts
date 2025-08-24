/**
 * API client for the Text2SQL backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface QueryRequest {
  question: string;
  page?: number;
  page_size?: number;
  stream?: boolean;
}

export interface QueryResponse {
  sql: string;
  columns: string[];
  rows: unknown[][];
  pagination?: {
    total_rows: number;
    has_more: boolean;
  };
}

export interface ExportRequest {
  question: string;
}

export interface ExportResponse {
  job_id: string;
  status: string;
}

export interface ExportStatusResponse {
  job_id: string;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  download_url?: string;
  row_count?: number;
  error?: string;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response: Response
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Query the database using natural language
 */
export async function query(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      `Query failed: ${errorText}`,
      response.status,
      response
    );
  }

  return response.json();
}

/**
 * Start an export job
 */
export async function startExport(request: ExportRequest): Promise<ExportResponse> {
  const response = await fetch(`${API_BASE_URL}/export/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      `Export start failed: ${errorText}`,
      response.status,
      response
    );
  }

  return response.json();
}

/**
 * Check the status of an export job
 */
export async function getExportStatus(jobId: string): Promise<ExportStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/export/status/${jobId}`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      `Export status check failed: ${errorText}`,
      response.status,
      response
    );
  }

  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ ok: boolean }> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      `Health check failed: ${errorText}`,
      response.status,
      response
    );
  }

  return response.json();
}

export { ApiError };