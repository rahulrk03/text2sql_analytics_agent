"use client";

import { useState } from "react";
import { query, QueryResponse, ApiError } from "@/lib/api";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleQuery = async () => {
    if (!question.trim()) return;
    
    setLoading(true);
    setError("");
    setResults(null);
    
    try {
      const data = await query({
        question: question.trim(),
        page: 1,
        page_size: 50,
        stream: false
      });
      setResults(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "An error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Text2SQL Analytics Agent
          </h1>
          
          <div className="mb-6">
            <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
              Ask a question about your data:
            </label>
            <div className="flex gap-4">
              <input
                id="question"
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., How many customers do we have in each city?"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => e.key === "Enter" && handleQuery()}
              />
              <button
                onClick={handleQuery}
                disabled={loading || !question.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? "Querying..." : "Query"}
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {results && (
            <div className="space-y-6">
              <div className="bg-gray-50 p-4 rounded-md">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Generated SQL:</h3>
                <pre className="bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto">
                  {results.sql}
                </pre>
              </div>

              {results.rows && results.rows.length > 0 && (
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Results:</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full bg-white border border-gray-200">
                      <thead className="bg-gray-100">
                        <tr>
                          {results.columns.map((col: string, idx: number) => (
                            <th key={idx} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {results.rows.map((row: unknown[], idx: number) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            {row.map((cell: unknown, cellIdx: number) => (
                              <td key={cellIdx} className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border-b">
                                {cell !== null ? String(cell) : "null"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  
                  {results.pagination && (
                    <div className="mt-4 text-sm text-gray-600">
                      Showing {results.pagination.total_rows} total rows
                      {results.pagination.has_more && " (more available)"}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="mt-8 border-t pt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">About</h3>
            <p className="text-gray-600">
              This Text2SQL Analytics Agent converts your natural language questions into SQL queries 
              and executes them against your database. It uses AI to understand your questions and 
              generate safe, read-only SQL queries.
            </p>
            
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-900">Natural Language</h4>
                <p className="text-blue-700 text-sm">Ask questions in plain English</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="font-semibold text-green-900">AI-Powered</h4>
                <p className="text-green-700 text-sm">Uses OpenAI to generate SQL</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-semibold text-purple-900">Secure</h4>
                <p className="text-purple-700 text-sm">Only safe, read-only queries</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
