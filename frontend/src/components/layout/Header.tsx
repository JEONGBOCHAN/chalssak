'use client';

import Link from 'next/link';

export default function Header() {
  return (
    <header className="h-14 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between px-4 fixed top-0 left-0 right-0 z-50">
      <div className="flex items-center gap-4">
        <Link href="/" className="font-bold text-xl text-gray-900 dark:text-white">
          Chalssak
        </Link>
      </div>

      <nav className="flex items-center gap-4">
        <Link
          href="/channels"
          className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          Channels
        </Link>
        <Link
          href="/search"
          className="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          Search
        </Link>
      </nav>
    </header>
  );
}
