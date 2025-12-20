import { test, expect } from '@playwright/test';
import {
  createChannel,
  getChannel,
  listChannels,
  deleteChannel,
  cleanupTestChannels,
  healthCheck,
} from './helpers/api';

test.describe('Channel API E2E Tests', () => {
  // Clean up test channels after all tests
  test.afterAll(async ({ request }) => {
    await cleanupTestChannels(request, 'E2E Test');
  });

  test.describe('Health Check', () => {
    test('API server is running', async ({ request }) => {
      const health = await healthCheck(request);
      expect(health.status).toBe('healthy');
    });
  });

  test.describe('Channel CRUD Flow', () => {
    let testChannelId: string;

    test('should create a new channel', async ({ request }) => {
      const channelName = `E2E Test Channel ${Date.now()}`;
      const response = await request.post('/api/v1/channels', {
        data: {
          name: channelName,
          description: 'Created by E2E test',
        },
      });

      expect(response.status()).toBe(201);

      const channel = await response.json();
      expect(channel.name).toBe(channelName);
      expect(channel.description).toBe('Created by E2E test');
      expect(channel.id).toBeTruthy();
      expect(channel.file_count).toBe(0);

      testChannelId = channel.id;
    });

    test('should list channels including the created one', async ({ request }) => {
      const { channels, total } = await listChannels(request);

      expect(total).toBeGreaterThan(0);
      expect(channels.length).toBeGreaterThan(0);

      // Find our test channel
      const testChannel = channels.find((c) => c.id === testChannelId);
      expect(testChannel).toBeTruthy();
    });

    test('should get channel by ID', async ({ request }) => {
      const channel = await getChannel(request, testChannelId);

      expect(channel).not.toBeNull();
      expect(channel!.id).toBe(testChannelId);
    });

    test('should update channel', async ({ request }) => {
      const newName = `E2E Test Updated ${Date.now()}`;
      const response = await request.put(`/api/v1/channels/${testChannelId}`, {
        data: {
          name: newName,
          description: 'Updated by E2E test',
        },
      });

      expect(response.status()).toBe(200);

      const channel = await response.json();
      expect(channel.name).toBe(newName);
      expect(channel.description).toBe('Updated by E2E test');
    });

    test('should delete channel', async ({ request }) => {
      const deleted = await deleteChannel(request, testChannelId);
      expect(deleted).toBe(true);

      // Verify deletion
      const channel = await getChannel(request, testChannelId);
      expect(channel).toBeNull();
    });
  });

  test.describe('Channel Validation', () => {
    test('should reject empty channel name', async ({ request }) => {
      const response = await request.post('/api/v1/channels', {
        data: { name: '' },
      });

      expect(response.status()).toBe(422);
    });

    test('should return 404 for non-existent channel', async ({ request }) => {
      const response = await request.get('/api/v1/channels/fileSearchStores/non-existent-id');

      expect(response.status()).toBe(404);
    });
  });

  test.describe('Channel List Pagination', () => {
    test('should support limit parameter', async ({ request }) => {
      const response = await request.get('/api/v1/channels?limit=5');

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data.channels.length).toBeLessThanOrEqual(5);
    });

    test('should support offset parameter', async ({ request }) => {
      const response = await request.get('/api/v1/channels?offset=0&limit=10');

      expect(response.status()).toBe(200);
    });
  });
});
