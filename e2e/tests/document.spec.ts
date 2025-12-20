import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import {
  createChannel,
  deleteChannel,
  listDocuments,
  cleanupTestChannels,
} from './helpers/api';

test.describe('Document API E2E Tests', () => {
  let testChannelId: string;
  const testChannelName = `E2E Test Documents ${Date.now()}`;

  // Create a test channel before all tests
  test.beforeAll(async ({ request }) => {
    const channel = await createChannel(request, testChannelName, 'For document tests');
    testChannelId = channel.id;
  });

  // Clean up after all tests
  test.afterAll(async ({ request }) => {
    await cleanupTestChannels(request, 'E2E Test');
  });

  test.describe('Document List', () => {
    test('should list documents in channel (empty initially)', async ({ request }) => {
      const { documents, total } = await listDocuments(request, testChannelId);

      expect(total).toBe(0);
      expect(documents).toEqual([]);
    });

    test('should return 404 for non-existent channel', async ({ request }) => {
      const response = await request.get(
        '/api/v1/documents?channel_id=fileSearchStores/non-existent'
      );

      expect(response.status()).toBe(404);
    });
  });

  test.describe('Document Upload Validation', () => {
    test('should reject upload without channel_id', async ({ request }) => {
      // Create a simple text file for testing
      const testContent = Buffer.from('Test document content');

      const response = await request.post('/api/v1/documents', {
        multipart: {
          file: {
            name: 'test.txt',
            mimeType: 'text/plain',
            buffer: testContent,
          },
        },
      });

      // Should fail without channel_id
      expect(response.status()).toBe(422);
    });

    test('should reject upload to non-existent channel', async ({ request }) => {
      const testContent = Buffer.from('Test document content');

      const response = await request.post(
        '/api/v1/documents?channel_id=fileSearchStores/non-existent',
        {
          multipart: {
            file: {
              name: 'test.txt',
              mimeType: 'text/plain',
              buffer: testContent,
            },
          },
        }
      );

      expect(response.status()).toBe(404);
    });
  });

  test.describe('URL Upload', () => {
    test('should reject invalid URL', async ({ request }) => {
      const response = await request.post(
        `/api/v1/documents/url?channel_id=${testChannelId}`,
        {
          data: {
            url: 'not-a-valid-url',
          },
        }
      );

      expect(response.status()).toBe(422);
    });

    test('should reject upload to non-existent channel', async ({ request }) => {
      const response = await request.post(
        '/api/v1/documents/url?channel_id=fileSearchStores/non-existent',
        {
          data: {
            url: 'https://example.com',
          },
        }
      );

      expect(response.status()).toBe(404);
    });
  });

  test.describe('Document Delete', () => {
    test('should return error for non-existent document', async ({ request }) => {
      const response = await request.delete('/api/v1/documents/files/non-existent-doc');

      // Should fail (500 because Gemini API returns error)
      expect(response.status()).toBe(500);
    });
  });
});
