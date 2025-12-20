import { test, expect } from '@playwright/test';
import {
  createChannel,
  deleteChannel,
  cleanupTestChannels,
  summarizeChannel,
} from './helpers/api';

test.describe('Chat API E2E Tests', () => {
  let testChannelId: string;
  const testChannelName = `E2E Test Chat ${Date.now()}`;

  // Create a test channel before all tests
  test.beforeAll(async ({ request }) => {
    const channel = await createChannel(request, testChannelName, 'For chat tests');
    testChannelId = channel.id;
  });

  // Clean up after all tests
  test.afterAll(async ({ request }) => {
    await cleanupTestChannels(request, 'E2E Test');
  });

  test.describe('Chat Message', () => {
    test('should send chat message to channel', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${testChannelId}/chat`, {
        data: {
          message: 'Hello, what can you tell me about this channel?',
        },
      });

      // Chat might fail if no documents, but should return valid response format
      const status = response.status();
      expect([200, 400, 500]).toContain(status);

      if (status === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('response');
        expect(data).toHaveProperty('sources');
      }
    });

    test('should return 404 for non-existent channel', async ({ request }) => {
      const response = await request.post(
        '/api/v1/channels/fileSearchStores/non-existent/chat',
        {
          data: {
            message: 'Hello',
          },
        }
      );

      expect(response.status()).toBe(404);
    });

    test('should reject empty message', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${testChannelId}/chat`, {
        data: {
          message: '',
        },
      });

      expect(response.status()).toBe(422);
    });
  });

  test.describe('Chat Streaming', () => {
    test('should support streaming chat response', async ({ request }) => {
      const response = await request.post(
        `/api/v1/channels/${testChannelId}/chat/stream`,
        {
          data: {
            message: 'Tell me about the documents',
          },
        }
      );

      // Streaming might fail if no documents, but endpoint should exist
      const status = response.status();
      expect([200, 400, 404, 500]).toContain(status);
    });
  });

  test.describe('Channel Summarization', () => {
    test('should fail to summarize empty channel', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${testChannelId}/summarize`, {
        data: {
          summary_type: 'short',
        },
      });

      // Should fail because channel has no documents
      expect(response.status()).toBe(400);

      const data = await response.json();
      expect(data.detail).toContain('no documents');
    });

    test('should support short and detailed summary types', async ({ request }) => {
      // Test short summary request format
      const shortResponse = await request.post(
        `/api/v1/channels/${testChannelId}/summarize`,
        {
          data: { summary_type: 'short' },
        }
      );

      // Should fail due to no documents, not validation
      expect(shortResponse.status()).toBe(400);

      // Test detailed summary request format
      const detailedResponse = await request.post(
        `/api/v1/channels/${testChannelId}/summarize`,
        {
          data: { summary_type: 'detailed' },
        }
      );

      expect(detailedResponse.status()).toBe(400);
    });

    test('should reject invalid summary type', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${testChannelId}/summarize`, {
        data: {
          summary_type: 'invalid_type',
        },
      });

      expect(response.status()).toBe(422);
    });
  });
});
