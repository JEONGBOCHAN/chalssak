import { test, expect } from '@playwright/test';
import {
  createChannel,
  getChannel,
  listChannels,
  deleteChannel,
  listDocuments,
  cleanupTestChannels,
  healthCheck,
} from './helpers/api';

/**
 * User Flow E2E Tests
 *
 * These tests simulate complete user journeys through the API:
 * 1. Channel creation → Document management → Chat
 * 2. Channel list → Search → View details
 * 3. Admin operations
 */

test.describe('Complete User Flow Tests', () => {
  // Clean up test channels after all tests
  test.afterAll(async ({ request }) => {
    await cleanupTestChannels(request, 'E2E Flow');
  });

  test.describe('Flow 1: Channel Creation to Chat', () => {
    let channelId: string;
    const channelName = `E2E Flow Test ${Date.now()}`;

    test('Step 1: Verify API is healthy', async ({ request }) => {
      const health = await healthCheck(request);
      expect(health.status).toBe('healthy');
    });

    test('Step 2: Create a new channel', async ({ request }) => {
      const channel = await createChannel(
        request,
        channelName,
        'E2E Flow Test - Full user journey'
      );

      expect(channel.id).toBeTruthy();
      expect(channel.name).toBe(channelName);
      channelId = channel.id;
    });

    test('Step 3: Verify channel appears in list', async ({ request }) => {
      const { channels } = await listChannels(request);

      const found = channels.find((c) => c.id === channelId);
      expect(found).toBeTruthy();
      expect(found!.name).toBe(channelName);
    });

    test('Step 4: Get channel details', async ({ request }) => {
      const channel = await getChannel(request, channelId);

      expect(channel).not.toBeNull();
      expect(channel!.id).toBe(channelId);
      expect(channel!.file_count).toBe(0);
    });

    test('Step 5: List documents (should be empty)', async ({ request }) => {
      const { documents, total } = await listDocuments(request, channelId);

      expect(total).toBe(0);
      expect(documents).toEqual([]);
    });

    test('Step 6: Attempt chat (should handle gracefully)', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${channelId}/chat`, {
        data: {
          message: 'What documents are available?',
        },
      });

      // Should handle empty channel gracefully
      const status = response.status();
      expect([200, 400, 500]).toContain(status);
    });

    test('Step 7: Attempt summarization (should fail - no docs)', async ({ request }) => {
      const response = await request.post(`/api/v1/channels/${channelId}/summarize`, {
        data: { summary_type: 'short' },
      });

      expect(response.status()).toBe(400);
    });

    test('Step 8: Update channel metadata', async ({ request }) => {
      const updatedName = `${channelName} - Updated`;
      const response = await request.put(`/api/v1/channels/${channelId}`, {
        data: {
          name: updatedName,
          description: 'Updated description',
        },
      });

      expect(response.status()).toBe(200);
      const channel = await response.json();
      expect(channel.name).toBe(updatedName);
    });

    test('Step 9: Delete channel', async ({ request }) => {
      const deleted = await deleteChannel(request, channelId);
      expect(deleted).toBe(true);
    });

    test('Step 10: Verify channel is deleted', async ({ request }) => {
      const channel = await getChannel(request, channelId);
      expect(channel).toBeNull();
    });
  });

  test.describe('Flow 2: Multiple Channels Management', () => {
    const channelIds: string[] = [];
    const numChannels = 3;

    test('Create multiple channels', async ({ request }) => {
      for (let i = 0; i < numChannels; i++) {
        const channel = await createChannel(
          request,
          `E2E Flow Multi ${i + 1} - ${Date.now()}`,
          `Multi-channel test ${i + 1}`
        );
        channelIds.push(channel.id);
      }

      expect(channelIds.length).toBe(numChannels);
    });

    test('List all channels with pagination', async ({ request }) => {
      // Get first page
      const response1 = await request.get('/api/v1/channels?limit=2&offset=0');
      expect(response1.status()).toBe(200);
      const page1 = await response1.json();
      expect(page1.channels.length).toBeLessThanOrEqual(2);

      // Get second page
      const response2 = await request.get('/api/v1/channels?limit=2&offset=2');
      expect(response2.status()).toBe(200);
    });

    test('Clean up all test channels', async ({ request }) => {
      for (const id of channelIds) {
        await deleteChannel(request, id);
      }
    });
  });

  test.describe('Flow 3: Error Handling', () => {
    test('Handle non-existent channel gracefully', async ({ request }) => {
      const fakeId = 'fileSearchStores/fake-channel-12345';

      // Get
      const getResponse = await request.get(`/api/v1/channels/${fakeId}`);
      expect(getResponse.status()).toBe(404);

      // Update
      const updateResponse = await request.put(`/api/v1/channels/${fakeId}`, {
        data: { name: 'New Name' },
      });
      expect(updateResponse.status()).toBe(404);

      // Chat
      const chatResponse = await request.post(`/api/v1/channels/${fakeId}/chat`, {
        data: { message: 'Hello' },
      });
      expect(chatResponse.status()).toBe(404);

      // Summarize
      const summarizeResponse = await request.post(`/api/v1/channels/${fakeId}/summarize`, {
        data: { summary_type: 'short' },
      });
      expect(summarizeResponse.status()).toBe(404);
    });

    test('Handle invalid request data', async ({ request }) => {
      // Empty channel name
      const response1 = await request.post('/api/v1/channels', {
        data: { name: '' },
      });
      expect(response1.status()).toBe(422);

      // Invalid summary type
      const channel = await createChannel(request, `E2E Flow Error Test ${Date.now()}`);
      const response2 = await request.post(`/api/v1/channels/${channel.id}/summarize`, {
        data: { summary_type: 'invalid' },
      });
      expect(response2.status()).toBe(422);

      await deleteChannel(request, channel.id);
    });
  });
});

test.describe('Admin API Tests', () => {
  test('Get system statistics', async ({ request }) => {
    const response = await request.get('/api/v1/admin/stats');

    expect(response.status()).toBe(200);

    const stats = await response.json();
    expect(stats).toHaveProperty('channels');
    expect(stats).toHaveProperty('storage');
    expect(stats).toHaveProperty('api');
  });

  test('Get API metrics', async ({ request }) => {
    const response = await request.get('/api/v1/admin/api-metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics).toHaveProperty('uptime_seconds');
    expect(metrics).toHaveProperty('total_api_calls');
  });

  test('Get channel breakdown', async ({ request }) => {
    const response = await request.get('/api/v1/admin/channels');

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('channels');
    expect(data).toHaveProperty('total');
  });
});
