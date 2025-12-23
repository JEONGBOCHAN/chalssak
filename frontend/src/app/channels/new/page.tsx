'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * /channels/new 경로 처리
 *
 * Next.js App Router에서 /channels/[id] 동적 라우트가 "new"를 ID로 인식하는 문제 해결.
 * 이 페이지는 /channels?create=true로 리다이렉트하여 채널 생성 모달을 엽니다.
 */
export default function NewChannelPage() {
  const router = useRouter();

  useEffect(() => {
    // 채널 생성 모달을 열기 위해 리다이렉트
    router.replace('/channels?create=true');
  }, [router]);

  // 리다이렉트 중 로딩 표시
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col items-center gap-3">
        <svg
          className="animate-spin h-8 w-8 text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Opening channel creator...
        </p>
      </div>
    </div>
  );
}
