// frontend/src/components/__tests__/GameImage.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import GameImage from '../GameImage';

// Mock the config/api module
vi.mock('../../config/api', () => ({
  imageProxyUrl: (url) => `/api/proxy?url=${encodeURIComponent(url)}`,
  generateSrcSet: (url) => {
    if (!url) return null;
    return `/api/proxy?url=${encodeURIComponent(url)} 1x, /api/proxy?url=${encodeURIComponent(url)}&size=2x 2x`;
  },
}));

// Mock useLazyLoad hook
vi.mock('../../hooks/useLazyLoad', () => ({
  useImageLazyLoad: ({ enabled }) => ({
    ref: { current: null },
    shouldLoad: true, // Always return true for tests
  }),
}));

describe('GameImage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    test('renders image with valid URL', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test game"
          className="test-class"
        />
      );

      const img = container.querySelector('img');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('alt', 'Test game');
    });

    test('uses default alt text when not provided', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('alt', 'Game cover image');
    });

    test('applies custom className', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          className="custom-class"
        />
      );

      const img = container.querySelector('img');
      expect(img?.className).toContain('custom-class');
    });

    test('sets aspect ratio style', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          aspectRatio="16/9"
        />
      );

      const containerDiv = container.querySelector('.game-image-container');
      expect(containerDiv).toHaveStyle({ aspectRatio: '16/9' });
    });
  });

  describe('Fallback/Error Handling', () => {
    test('displays fallback when URL is null', () => {
      render(<GameImage url={null} alt="Test" />);

      expect(screen.getByText('No Image')).toBeInTheDocument();
    });

    test('displays fallback when URL is empty', () => {
      render(<GameImage url="" alt="Test" />);

      expect(screen.getByText('No Image')).toBeInTheDocument();
    });

    test('displays fallback when URL is undefined', () => {
      render(<GameImage url={undefined} alt="Test" />);

      expect(screen.getByText('No Image')).toBeInTheDocument();
    });

    test('displays fallback on image error', async () => {
      const { container } = render(
        <GameImage url="https://example.com/broken.jpg" alt="Test" />
      );

      const img = container.querySelector('img');
      expect(img).toBeInTheDocument();

      // Simulate image load error
      await act(async () => {
        img?.dispatchEvent(new Event('error'));
      });

      await waitFor(() => {
        expect(screen.getByText('No Image')).toBeInTheDocument();
      });
    });

    test('applies custom fallback class', () => {
      const { container } = render(
        <GameImage
          url={null}
          alt="Test"
          fallbackClass="custom-fallback"
        />
      );

      const fallback = screen.getByText('No Image').parentElement;
      expect(fallback?.className).toContain('custom-fallback');
    });
  });

  describe('Loading States', () => {
    test('shows loading placeholder initially', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      // Check for loading placeholder (has blur and pulse animation)
      const placeholder = container.querySelector('[aria-hidden="true"]');
      expect(placeholder).toBeInTheDocument();
    });

    test('hides loading placeholder after image loads', async () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      const img = container.querySelector('img');

      // Initially should have opacity-0
      expect(img?.className).toContain('opacity-0');

      // Simulate image load
      await act(async () => {
        img?.dispatchEvent(new Event('load'));
      });

      await waitFor(() => {
        expect(img?.className).toContain('opacity-100');
      });
    });
  });

  describe('Loading Strategies', () => {
    test('uses lazy loading by default', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      const img = container.querySelector('img');
      // When using IntersectionObserver, native loading is set to "eager"
      expect(img).toHaveAttribute('loading', 'eager');
    });

    test('uses eager loading when specified', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          loading="eager"
        />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('loading', 'eager');
    });

    test('supports fetch priority attribute', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          fetchPriority="high"
        />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('fetchpriority', 'high');
    });

    test('disables IntersectionObserver when specified', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          loading="lazy"
          useIntersectionObserver={false}
        />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('loading', 'lazy');
    });
  });

  describe('Responsive Images', () => {
    test('uses srcset by default for mobile optimization', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('srcset');
    });

    test('can disable srcset when useResponsive is false', () => {
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          useResponsive={false}
        />
      );

      const img = container.querySelector('img');
      expect(img).not.toHaveAttribute('srcset');
    });

    test('includes sizes attribute when using responsive images', () => {
      const customSizes = '(max-width: 640px) 100vw, 50vw';
      const { container } = render(
        <GameImage
          url="https://example.com/image.jpg"
          alt="Test"
          useResponsive={true}
          sizes={customSizes}
        />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('sizes', customSizes);
    });
  });

  describe('Accessibility', () => {
    test('has proper alt text', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Catan board game" />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('alt', 'Catan board game');
    });

    test('uses async decoding for performance', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      const img = container.querySelector('img');
      expect(img).toHaveAttribute('decoding', 'async');
    });

    test('marks loading placeholder as aria-hidden', () => {
      const { container } = render(
        <GameImage url="https://example.com/image.jpg" alt="Test" />
      );

      const placeholder = container.querySelector('[aria-hidden="true"]');
      expect(placeholder).toBeInTheDocument();
    });
  });

  describe('Image Proxy Integration', () => {
    test('routes images through proxy URL', () => {
      const originalUrl = 'https://cf.geekdo-images.com/test.jpg';
      const { container } = render(
        <GameImage url={originalUrl} alt="Test" />
      );

      const img = container.querySelector('img');
      expect(img?.src).toContain('/api/proxy');
      expect(img?.src).toContain(encodeURIComponent(originalUrl));
    });
  });
});
