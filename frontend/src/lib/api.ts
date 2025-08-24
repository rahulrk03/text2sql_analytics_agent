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
 * Query the database using natural language (non-streaming)
 */
export async function query(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ...request, stream: false }),
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
 * Query the database using natural language with streaming response
 */
export async function queryStream(
  request: QueryRequest,
  onChunk: (chunk: string) => void,
  onComplete: (data: QueryResponse) => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...request, stream: true }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(
        `Streaming query failed: ${errorText}`,
        response.status,
        response
      );
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Failed to get response reader');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Parse the complete response
          if (buffer.trim()) {
            try {
              const data = JSON.parse(buffer);
              onComplete(data);
            } catch (parseError) {
              console.error('Failed to parse streaming response:', parseError);
              onError(new Error('Failed to parse streaming response'));
            }
          }
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        onChunk(chunk);
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error('Unknown streaming error'));
  }
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

/**
 * Download CSV from tabular data
 */
export function downloadCSV(data: QueryResponse, filename: string = 'query-results.csv'): void {
  const csvContent = [
    // Header row
    data.columns.join(','),
    // Data rows
    ...data.rows.map(row => 
      row.map(cell => {
        // Handle null values and escape commas/quotes
        if (cell === null || cell === undefined) return '';
        const str = String(cell);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    )
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}

export { ApiError };