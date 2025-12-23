'use client';

import MainLayout from '@/components/layout/MainLayout';

/**
 * 설정 페이지
 *
 * 사용자 설정 관리 (Coming Soon)
 */
export default function SettingsPage() {
  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            Settings
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage your application preferences
          </p>
        </div>

        {/* Coming Soon Message */}
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-6">
            <svg
              className="w-10 h-10 text-gray-400 dark:text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Settings Coming Soon
          </h2>
          <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">
            We&apos;re working on settings for theme preferences, API key management,
            and other customization options.
          </p>
        </div>

        {/* Placeholder Settings Sections */}
        <div className="space-y-6 opacity-50 pointer-events-none">
          {/* Theme Section */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Appearance
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Dark Mode
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Toggle between light and dark theme
                </p>
              </div>
              <div className="w-12 h-6 bg-gray-200 dark:bg-gray-700 rounded-full" />
            </div>
          </div>

          {/* API Section */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              API Configuration
            </h3>
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Gemini API Key
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure your own API key for enhanced usage
              </p>
            </div>
          </div>

          {/* Data Section */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Data Management
            </h3>
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Export Data
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Download all your channels and documents
              </p>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
