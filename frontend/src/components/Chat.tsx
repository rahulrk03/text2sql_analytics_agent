"use client";

import { useState, useRef, useEffect } from "react";
import { queryStream, downloadCSV, QueryResponse, ApiError } from "@/lib/api";

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sql?: string;
  data?: QueryResponse;
  error?: string;
  streaming?: boolean;
}

interface ChatProps {
  className?: string;
}

export default function Chat({ className = "" }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'assistant',
      content: 'Hi! I\'m your Text2SQL Analytics Agent. Ask me any question about your data and I\'ll generate SQL queries and show you the results.',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setInput("");
    setIsStreaming(true);

    try {
      await queryStream(
        {
          question: userMessage.content,
          page: 1,
          page_size: 100,
          stream: true
        },
        (chunk: string) => {
          // Stream processing feedback
          console.log('Streaming chunk received:', chunk.length);
          setMessages(prev => 
            prev.map(msg => 
              msg.id === assistantMessage.id 
                ? { ...msg, content: 'Processing your query...' }
                : msg
            )
          );
        },
        (data: QueryResponse) => {
          // Determine if this is a statement result or tabular data
          const hasData = data.rows && data.rows.length > 0;
          
          let responseContent = `I generated this SQL query for you:\n\`\`\`sql\n${data.sql}\n\`\`\`\n\n`;
          
          if (hasData) {
            responseContent += `Found ${data.rows.length} result${data.rows.length === 1 ? '' : 's'}`;
            if (data.pagination && data.pagination.total_rows > data.rows.length) {
              responseContent += ` (showing first ${data.rows.length} of ${data.pagination.total_rows} total rows)`;
            }
            responseContent += '. The results are displayed in the table below.';
          } else {
            responseContent += 'The query executed successfully but returned no results.';
          }

          setMessages(prev => 
            prev.map(msg => 
              msg.id === assistantMessage.id 
                ? { 
                    ...msg, 
                    content: responseContent,
                    sql: data.sql,
                    data: hasData ? data : undefined,
                    streaming: false 
                  }
                : msg
            )
          );
        },
        (error: Error) => {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === assistantMessage.id 
                ? { 
                    ...msg, 
                    content: 'Sorry, I encountered an error while processing your query.',
                    error: error.message,
                    streaming: false 
                  }
                : msg
            )
          );
        }
      );
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'An unexpected error occurred';
      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantMessage.id 
            ? { 
                ...msg, 
                content: 'Sorry, I encountered an error while processing your query.',
                error: errorMessage,
                streaming: false 
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleExport = (message: Message) => {
    if (message.data) {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      downloadCSV(message.data, `query-results-${timestamp}.csv`);
    }
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.type === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {/* Message Content */}
              <div className="whitespace-pre-wrap break-words">
                {message.content}
                {message.streaming && (
                  <span className="inline-block w-2 h-5 bg-gray-400 animate-pulse ml-1" />
                )}
              </div>

              {/* Error Display */}
              {message.error && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  Error: {message.error}
                </div>
              )}

              {/* SQL Code Block */}
              {message.sql && (
                <div className="mt-2">
                  <pre className="bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto">
                    {message.sql}
                  </pre>
                </div>
              )}

              {/* Data Table */}
              {message.data && message.data.rows && message.data.rows.length > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">Query Results</span>
                    <button
                      onClick={() => handleExport(message)}
                      className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700"
                    >
                      Export CSV
                    </button>
                  </div>
                  <div className="overflow-x-auto max-h-64 border rounded">
                    <table className="min-w-full bg-white text-sm">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          {message.data.columns.map((col: string, idx: number) => (
                            <th
                              key={idx}
                              className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b"
                            >
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {message.data.rows.map((row: unknown[], idx: number) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            {row.map((cell: unknown, cellIdx: number) => (
                              <td
                                key={cellIdx}
                                className="px-3 py-2 whitespace-nowrap text-gray-900 border-b"
                              >
                                {cell !== null ? String(cell) : (
                                  <span className="text-gray-400 italic">null</span>
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {message.data.pagination && (
                    <div className="mt-2 text-xs text-gray-600">
                      Showing {message.data.rows.length} of {message.data.pagination.total_rows} total rows
                    </div>
                  )}
                </div>
              )}

              {/* Timestamp */}
              <div className={`text-xs mt-2 ${
                message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="border-t bg-white p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                adjustTextareaHeight();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Ask a question about your data... (Shift+Enter for new line)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 resize-none"
              style={{ minHeight: '40px', maxHeight: '120px' }}
              disabled={isStreaming}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed self-end"
          >
            {isStreaming ? (
              <div className="flex items-center gap-1">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Sending</span>
              </div>
            ) : (
              'Send'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}