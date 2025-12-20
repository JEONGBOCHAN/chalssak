import { APIRequestContext } from '@playwright/test';

/**
 * Helper functions for API E2E tests.
 */

export interface Channel {
  id: string;
  name: string;
  description?: string;
  file_count: number;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  status: string;
  channel_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ source: string; content: string }>;
}

/**
 * Channel API helpers
 */
export async function createChannel(
  request: APIRequestContext,
  name: string,
  description?: string
): Promise<Channel> {
  const response = await request.post('/api/v1/channels', {
    data: { name, description },
  });
  return response.json();
}

export async function getChannel(
  request: APIRequestContext,
  channelId: string
): Promise<Channel | null> {
  const response = await request.get(`/api/v1/channels/${channelId}`);
  if (response.status() === 404) return null;
  return response.json();
}

export async function listChannels(
  request: APIRequestContext
): Promise<{ channels: Channel[]; total: number }> {
  const response = await request.get('/api/v1/channels');
  return response.json();
}

export async function deleteChannel(
  request: APIRequestContext,
  channelId: string
): Promise<boolean> {
  const response = await request.delete(`/api/v1/channels/${channelId}`);
  return response.status() === 204;
}

/**
 * Document API helpers
 */
export async function listDocuments(
  request: APIRequestContext,
  channelId: string
): Promise<{ documents: Document[]; total: number }> {
  const response = await request.get(`/api/v1/documents?channel_id=${channelId}`);
  return response.json();
}

/**
 * Chat API helpers
 */
export async function sendChatMessage(
  request: APIRequestContext,
  channelId: string,
  message: string
): Promise<{ response: string; sources: any[] }> {
  const response = await request.post(`/api/v1/channels/${channelId}/chat`, {
    data: { message },
  });
  return response.json();
}

/**
 * Summarize API helpers
 */
export async function summarizeChannel(
  request: APIRequestContext,
  channelId: string,
  summaryType: 'short' | 'detailed' = 'short'
): Promise<{ summary: string; channel_id: string }> {
  const response = await request.post(`/api/v1/channels/${channelId}/summarize`, {
    data: { summary_type: summaryType },
  });
  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(
  request: APIRequestContext
): Promise<{ status: string }> {
  const response = await request.get('/api/v1/health');
  return response.json();
}

/**
 * Cleanup helper - delete all test channels
 */
export async function cleanupTestChannels(
  request: APIRequestContext,
  prefix: string = 'E2E Test'
): Promise<number> {
  const { channels } = await listChannels(request);
  let deleted = 0;

  for (const channel of channels) {
    if (channel.name.startsWith(prefix)) {
      await deleteChannel(request, channel.id);
      deleted++;
    }
  }

  return deleted;
}
