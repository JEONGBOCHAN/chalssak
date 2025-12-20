import apiClient from './client';

export interface ChatSource {
  source: string;
  content: string;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  created_at?: string;
}

export interface SummarizeRequest {
  summary_type: 'short' | 'detailed';
}

export interface SummarizeResponse {
  channel_id: string;
  document_id?: string;
  summary_type: 'short' | 'detailed';
  summary: string;
  generated_at: string;
}

export const chatApi = {
  sendMessage: (channelId: string, message: string) => {
    return apiClient.post<ChatResponse>(`/api/v1/channels/${channelId}/chat`, {
      message,
    });
  },

  getHistory: (channelId: string, limit?: number) => {
    const params = limit ? `?limit=${limit}` : '';
    return apiClient.get<{ messages: ChatMessage[] }>(
      `/api/v1/channels/${channelId}/chat/history${params}`
    );
  },

  clearHistory: (channelId: string) => {
    return apiClient.delete<void>(`/api/v1/channels/${channelId}/chat/history`);
  },

  summarizeChannel: (channelId: string, summaryType: 'short' | 'detailed' = 'short') => {
    return apiClient.post<SummarizeResponse>(`/api/v1/channels/${channelId}/summarize`, {
      summary_type: summaryType,
    });
  },

  summarizeDocument: (
    channelId: string,
    documentId: string,
    summaryType: 'short' | 'detailed' = 'short'
  ) => {
    return apiClient.post<SummarizeResponse>(
      `/api/v1/channels/${channelId}/documents/${documentId}/summarize`,
      { summary_type: summaryType }
    );
  },
};

export default chatApi;
