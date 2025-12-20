'use client';

import type { ChatMessage as ChatMessageType, ChatSource } from '@/lib/api/chat';
import SourceCitation from './SourceCitation';

interface ChatMessageProps {
  message: ChatMessageType;
  onSaveAsNote?: (content: string, sources: ChatSource[]) => void;
}

export default function ChatMessage({ message, onSaveAsNote }: ChatMessageProps) {
  const isUser = message.role === 'user';

  const formatTime = (dateString?: string) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`flex items-start gap-3 py-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-gray-200 dark:bg-gray-700'
            : 'bg-blue-100 dark:bg-blue-900'
        }`}
      >
        {isUser ? (
          <svg
            className="w-4 h-4 text-gray-600 dark:text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        ) : (
          <svg
            className="w-4 h-4 text-blue-600 dark:text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Sources for AI messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitation sources={message.sources} />
        )}

        {/* Footer */}
        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : ''}`}>
          {message.created_at && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {formatTime(message.created_at)}
            </span>
          )}

          {/* Save as Note button for AI messages */}
          {!isUser && onSaveAsNote && (
            <button
              onClick={() => onSaveAsNote(message.content, message.sources || [])}
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
            >
              <svg
                className="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                />
              </svg>
              Save as note
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
