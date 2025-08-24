"use client";

import Chat from "@/components/Chat";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white border-b shadow-sm">
          <div className="px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Text2SQL Analytics Agent
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Ask questions about your data in natural language
            </p>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="h-[calc(100vh-120px)]">
          <Chat className="h-full bg-white" />
        </div>
      </div>
    </div>
  );
}
