'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';

/**
 * 검색 페이지
 *
 * 채널 및 문서 전체 검색 기능 (Coming Soon)
 */
export default function SearchPage() {
  const [query, setQuery] = useState('');

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            Search
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Search across all your channels and documents
          </p>
        </div>

        {/* Search Input */}
        <div className="mb-8">
          <div className="relative">
            <svg
              className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search channels, documents, or content..."
              className="w-full pl-12 pr-4 py-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Coming Soon Message */}
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-20 h-20 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-6">
            <svg
              className="w-10 h-10 text-blue-600 dark:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Global Search Coming Soon
          </h2>
          <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">
            We&apos;re working on a powerful search feature that will let you find
            content across all your channels and documents instantly.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-4">
            For now, use the chat feature within each channel to search documents.
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
