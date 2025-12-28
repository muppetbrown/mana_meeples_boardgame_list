// frontend/src/config/__tests__/api.test.js
import { describe, it, expect } from 'vitest';
import { imageProxyUrl, generateSrcSet, API_BASE } from '../api';

describe('API Config', () => {
  describe('imageProxyUrl', () => {
    it('returns null for empty URL', () => {
      expect(imageProxyUrl('')).toBeNull();
      expect(imageProxyUrl(null)).toBeNull();
      expect(imageProxyUrl(undefined)).toBeNull();
    });

    it('proxies BGG images', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = imageProxyUrl(url);

      expect(result).toContain('/api/public/image-proxy');
      expect(result).toContain('url=');
    });

    it('includes width parameter when provided', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = imageProxyUrl(url, 'original', 400);

      expect(result).toContain('width=400');
    });

    it('includes height parameter when provided', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = imageProxyUrl(url, 'original', null, 300);

      expect(result).toContain('height=300');
    });

    it('includes both width and height parameters', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = imageProxyUrl(url, 'original', 400, 300);

      expect(result).toContain('width=400');
      expect(result).toContain('height=300');
    });

    it('proxies non-BGG images as-is', () => {
      const url = 'https://example.com/image.jpg';
      const result = imageProxyUrl(url);

      expect(result).toContain('/api/public/image-proxy');
      expect(result).toContain(encodeURIComponent(url));
    });
  });

  describe('generateSrcSet', () => {
    it('returns null for empty URL', () => {
      expect(generateSrcSet('')).toBeNull();
      expect(generateSrcSet(null)).toBeNull();
      expect(generateSrcSet(undefined)).toBeNull();
    });

    it('returns null for non-BGG images', () => {
      const url = 'https://example.com/image.jpg';
      expect(generateSrcSet(url)).toBeNull();
    });

    it('generates srcset for BGG images', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = generateSrcSet(url);

      expect(result).toContain('200w');
      expect(result).toContain('400w');
      expect(result).toContain('600w');
      expect(result).toContain('800w');
      expect(result).toContain('1200w');
    });

    it('srcset includes width and height parameters', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = generateSrcSet(url);

      expect(result).toContain('width=200&height=200');
      expect(result).toContain('width=400&height=400');
    });

    it('srcset entries are comma-separated', () => {
      const url = 'https://cf.geekdo-images.com/original/img/abc.jpg';
      const result = generateSrcSet(url);

      const entries = result.split(', ');
      expect(entries).toHaveLength(5);
      entries.forEach(entry => {
        expect(entry).toMatch(/\d+w$/);
      });
    });
  });

  describe('API_BASE resolution', () => {
    it('API_BASE is defined', () => {
      expect(API_BASE).toBeDefined();
      expect(typeof API_BASE).toBe('string');
    });

    it('API_BASE does not have trailing slash', () => {
      expect(API_BASE).not.toMatch(/\/$/);
    });
  });
});
