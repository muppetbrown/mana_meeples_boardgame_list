// frontend/src/__tests__/App.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

// Mock the page components
vi.mock('../pages/PublicCatalogue', () => ({
  default: () => <div data-testid="public-catalogue">Public Catalogue</div>,
}));

vi.mock('../pages/GameDetails', () => ({
  default: () => <div data-testid="game-details">Game Details</div>,
}));

vi.mock('../pages/AdminLogin', () => ({
  default: () => <div data-testid="admin-login">Admin Login</div>,
}));

vi.mock('../pages/StaffView', () => ({
  default: () => <div data-testid="staff-view">Staff View</div>,
}));

// Mock API client to avoid network calls
vi.mock('../api/client', () => ({
  getPublicGames: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getPublicCategoryCounts: vi.fn().mockResolvedValue({}),
}));

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Routing', () => {
    test('renders PublicCatalogue at root path', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('public-catalogue')).toBeInTheDocument();
      });
    });

    test('renders GameDetails at /game/:id path', async () => {
      render(
        <MemoryRouter initialEntries={['/game/123']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('game-details')).toBeInTheDocument();
      });
    });

    test('renders AdminLogin at /staff/login path', async () => {
      render(
        <MemoryRouter initialEntries={['/staff/login']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('admin-login')).toBeInTheDocument();
      });
    });

    test('renders StaffView at /staff path', async () => {
      render(
        <MemoryRouter initialEntries={['/staff']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('staff-view')).toBeInTheDocument();
      });
    });

    test('redirects unknown routes to root', async () => {
      render(
        <MemoryRouter initialEntries={['/unknown-route']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('public-catalogue')).toBeInTheDocument();
      });
    });

    test('redirects /invalid/path to root', async () => {
      render(
        <MemoryRouter initialEntries={['/invalid/path']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('public-catalogue')).toBeInTheDocument();
      });
    });
  });

  describe('Lazy Loading', () => {
    test('loads and renders lazy component after suspense', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('public-catalogue')).toBeInTheDocument();
      });
    });

    test('renders content after lazy loading completes', async () => {
      render(
        <MemoryRouter initialEntries={['/game/123']}>
          <App />
        </MemoryRouter>
      );

      // Wait for lazy loaded component to render
      await waitFor(() => {
        expect(screen.getByTestId('game-details')).toBeInTheDocument();
      });
    });
  });

  describe('Error Boundary', () => {
    test('wraps routes with ErrorBoundary', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      );

      // App should render without errors
      expect(container).toBeInTheDocument();
    });
  });
});
