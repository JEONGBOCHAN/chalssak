'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { ChatContainer } from '@/components/chat';
import { DocumentUploader, DocumentList } from '@/components/documents';
import { NotesList, NoteEditor, DeleteNoteModal } from '@/components/notes';
import { channelsApi, type Channel } from '@/lib/api/channels';
import { notesApi, type Note, type CreateNoteRequest, type UpdateNoteRequest } from '@/lib/api/notes';
import type { ChatSource } from '@/lib/api/types';

type ViewTab = 'chat' | 'notes';

export default function ChannelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const channelId = params.id as string;

  const [channel, setChannel] = useState<Channel | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDocuments, setShowDocuments] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState<ViewTab>('chat');

  // Notes state
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoadingNotes, setIsLoadingNotes] = useState(true);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isCreatingNote, setIsCreatingNote] = useState(false);
  const [noteToDelete, setNoteToDelete] = useState<Note | null>(null);

  // Track current request to prevent race conditions
  const requestIdRef = useRef(0);

  // Unified data fetching - prevents race conditions by tracking request IDs
  useEffect(() => {
    const currentRequestId = ++requestIdRef.current;

    async function fetchData() {
      setIsLoading(true);
      setIsLoadingNotes(true);
      setError(null);

      try {
        // Fetch channel and notes in parallel
        const [channelData, notesData] = await Promise.all([
          channelsApi.get(channelId),
          notesApi.list(channelId),
        ]);

        // Only update state if this is still the current request
        if (currentRequestId !== requestIdRef.current) {
          return; // Stale response, ignore
        }

        setChannel(channelData);
        setNotes(notesData.notes);
      } catch (err) {
        // Only update error if this is still the current request
        if (currentRequestId !== requestIdRef.current) {
          return;
        }

        setError(err instanceof Error ? err.message : 'Failed to load channel');
        setChannel(null);
        setNotes([]);
      } finally {
        // Only update loading state if this is still the current request
        if (currentRequestId === requestIdRef.current) {
          setIsLoading(false);
          setIsLoadingNotes(false);
        }
      }
    }

    // Reset state when channelId changes
    setChannel(null);
    setNotes([]);
    setSelectedNote(null);
    setIsCreatingNote(false);

    fetchData();
  }, [channelId]);

  // Refresh channel data (e.g., after upload)
  const refreshChannel = async () => {
    try {
      const data = await channelsApi.get(channelId);
      setChannel(data);
    } catch (err) {
      console.error('Failed to refresh channel:', err);
    }
  };

  // Refresh notes only
  const refreshNotes = async () => {
    try {
      const data = await notesApi.list(channelId);
      setNotes(data.notes);
    } catch (err) {
      console.error('Failed to refresh notes:', err);
    }
  };

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
    refreshChannel(); // Refresh channel to update file count
  };

  const handleSaveAsNote = async (content: string, sources: ChatSource[]) => {
    // Create a note from chat response with sources
    try {
      const title = content.slice(0, 50).replace(/[#*`\n]/g, '').trim() || 'New Note';
      const newNote = await notesApi.create(channelId, {
        title,
        content,
        sources,
      });
      setNotes((prev) => [newNote, ...prev]);
      setSelectedNote(newNote);
      setIsCreatingNote(false);
      setActiveTab('notes');
    } catch (err) {
      console.error('Failed to save as note:', err);
    }
  };

  // Note handlers
  const handleCreateNote = () => {
    setSelectedNote(null);
    setIsCreatingNote(true);
  };

  const handleSelectNote = (note: Note) => {
    setIsCreatingNote(false);
    setSelectedNote(note);
  };

  const handleSaveNote = async (data: CreateNoteRequest | UpdateNoteRequest) => {
    if (isCreatingNote) {
      const newNote = await notesApi.create(channelId, data as CreateNoteRequest);
      setNotes((prev) => [newNote, ...prev]);
      setSelectedNote(newNote);
      setIsCreatingNote(false);
    } else if (selectedNote) {
      const updatedNote = await notesApi.update(channelId, selectedNote.id, data as UpdateNoteRequest);
      setNotes((prev) =>
        prev.map((n) => (n.id === updatedNote.id ? updatedNote : n))
      );
      setSelectedNote(updatedNote);
    }
  };

  const handleDeleteNote = async () => {
    if (!noteToDelete) return;
    await notesApi.delete(channelId, noteToDelete.id);
    setNotes((prev) => prev.filter((n) => n.id !== noteToDelete.id));
    if (selectedNote?.id === noteToDelete.id) {
      setSelectedNote(null);
      setIsCreatingNote(false);
    }
  };

  const handleCancelCreate = () => {
    setIsCreatingNote(false);
    if (notes.length > 0) {
      setSelectedNote(notes[0]);
    }
  };

  if (isLoading) {
    return (
      <MainLayout showSidebar={false}>
        <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
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
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading channel...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error || !channel) {
    return (
      <MainLayout showSidebar={false}>
        <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)]">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
            <svg
              className="w-8 h-8 text-red-600 dark:text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Channel not found
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {error || 'The channel you are looking for does not exist.'}
          </p>
          <button
            onClick={() => router.push('/channels')}
            className="px-4 py-2 bg-blue-600 text-sm text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Back to channels
          </button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout showSidebar={false}>
      <div className="h-[calc(100vh-5rem)] flex flex-col">
        {/* Channel Header */}
        <div className="flex items-center gap-4 px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <button
            onClick={() => router.push('/channels')}
            className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <svg
              className="w-5 h-5 text-gray-600 dark:text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {channel.name}
            </h1>
            {channel.description && (
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                {channel.description}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Tab Switcher */}
            <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-md p-0.5 mr-2">
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activeTab === 'chat'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Chat
              </button>
              <button
                onClick={() => setActiveTab('notes')}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                  activeTab === 'notes'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Notes
                {notes.length > 0 && (
                  <span className="text-xs bg-gray-200 dark:bg-gray-600 px-1.5 rounded-full">
                    {notes.length}
                  </span>
                )}
              </button>
            </div>

            <span className="text-xs text-gray-400 dark:text-gray-500">
              {channel.file_count} files
            </span>
            <button
              onClick={() => setShowDocuments(!showDocuments)}
              className={`p-2 rounded-md transition-colors ${
                showDocuments
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
              }`}
              title={showDocuments ? 'Hide documents' : 'Show documents'}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar - Documents (for chat) or Notes List (for notes) */}
          {activeTab === 'chat' ? (
            showDocuments && (
              <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 overflow-y-auto">
                <div className="p-4 space-y-4">
                  {/* Upload Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                      Add Documents
                    </h3>
                    <DocumentUploader
                      channelId={channelId}
                      onUploadComplete={handleUploadComplete}
                    />
                  </div>

                  {/* Document List */}
                  <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                    <DocumentList
                      channelId={channelId}
                      refreshTrigger={refreshTrigger}
                    />
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              <NotesList
                notes={notes}
                selectedNoteId={selectedNote?.id ?? null}
                onSelectNote={handleSelectNote}
                onCreateNote={handleCreateNote}
                onDeleteNote={(note) => setNoteToDelete(note)}
                isLoading={isLoadingNotes}
              />
            </div>
          )}

          {/* Main Area - Chat or Note Editor */}
          <div className="flex-1 flex flex-col bg-white dark:bg-gray-900 overflow-hidden">
            {activeTab === 'chat' ? (
              <ChatContainer channelId={channelId} onSaveAsNote={handleSaveAsNote} />
            ) : (
              <>
                {isCreatingNote ? (
                  <NoteEditor
                    note={null}
                    isNew={true}
                    onSave={handleSaveNote}
                    onCancel={handleCancelCreate}
                    autoSaveDelay={0}
                  />
                ) : selectedNote ? (
                  <NoteEditor
                    key={selectedNote.id}
                    note={selectedNote}
                    onSave={handleSaveNote}
                    autoSaveDelay={2000}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                    <div className="text-center">
                      <svg
                        className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                        No note selected
                      </h3>
                      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        Select a note from the sidebar or create a new one
                      </p>
                      <button
                        onClick={handleCreateNote}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 4v16m8-8H4"
                          />
                        </svg>
                        New Note
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Delete Note Modal */}
      <DeleteNoteModal
        isOpen={!!noteToDelete}
        note={noteToDelete}
        onClose={() => setNoteToDelete(null)}
        onConfirm={handleDeleteNote}
      />
    </MainLayout>
  );
}
