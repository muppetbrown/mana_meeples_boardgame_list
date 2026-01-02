# Frontend Test Guide

## Overview

This guide provides templates and best practices for improving frontend test coverage from the current 62.77% to the target 80%+.

## Current Test Coverage

### Existing Tests ✅
- `App.test.jsx`
- `components/__tests__/CategoryFilter.test.jsx`
- `components/__tests__/CategorySelectModal.test.jsx`
- `components/public/__tests__/GameCardPublic.test.jsx`
- `components/public/__tests__/Pagination.test.jsx`
- `components/public/__tests__/SearchBox.test.jsx`

### Missing Tests ⚠️
- **Hooks**: `useAuth`, `useGameFilters`, `useToast`, `useOnboarding`, `useInfiniteScroll`
- **Pages**: `PublicCatalogue`, `GameDetails`, `StaffView`, `AdminLogin`
- **API Client**: `api/client.js`
- **Config**: `config/api.js`
- **Utils**: Various utility functions

## Test Structure

### Basic Test Template
```javascript
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Component from './Component';

describe('Component', () => {
  test('renders correctly', () => {
    render(
      <BrowserRouter>
        <Component />
      </BrowserRouter>
    );
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

## Priority Test Templates

### 1. Hook Tests (HIGH PRIORITY)

#### Template: `hooks/__tests__/useAuth.test.js`
```javascript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '../useAuth';

// Mock the API client
jest.mock('../../api/client', () => ({
  adminLogin: jest.fn(),
  validateAdminToken: jest.fn(),
  adminLogout: jest.fn(),
}));

describe('useAuth Hook', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  test('initializes with no auth', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
  });

  test('logs in successfully', async () => {
    const { adminLogin } = require('../../api/client');
    adminLogin.mockResolvedValue({
      data: { token: 'test-token', success: true }
    });

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.login('test-token');
    });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.token).toBe('test-token');
    });
  });

  test('handles login failure', async () => {
    const { adminLogin } = require('../../api/client');
    adminLogin.mockRejectedValue(new Error('Invalid token'));

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await expect(result.current.login('bad-token')).rejects.toThrow();
    });

    expect(result.current.isAuthenticated).toBe(false);
  });

  test('logs out successfully', async () => {
    localStorage.setItem('adminToken', 'test-token');

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorage.getItem('adminToken')).toBeNull();
  });

  test('persists token across renders', () => {
    localStorage.setItem('adminToken', 'persisted-token');

    const { result } = renderHook(() => useAuth());

    expect(result.current.token).toBe('persisted-token');
  });
});
```

#### Template: `hooks/__tests__/useGameFilters.test.js`
```javascript
import { renderHook, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { useGameFilters } from '../useGameFilters';

const wrapper = ({ children }) => <BrowserRouter>{children}</BrowserRouter>;

describe('useGameFilters Hook', () => {
  test('initializes with default filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    expect(result.current.filters).toEqual({
      q: '',
      category: 'all',
      designer: '',
      nz_designer: false,
      players: '',
      complexity: '',
      sort: 'title_asc',
    });
  });

  test('updates search query', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.setFilter('q', 'Catan');
    });

    expect(result.current.filters.q).toBe('Catan');
  });

  test('updates URL parameters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.setFilter('category', 'GATEWAY_STRATEGY');
    });

    // Check URL contains the filter
    expect(window.location.search).toContain('category=GATEWAY_STRATEGY');
  });

  test('clears all filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.setFilter('q', 'Catan');
      result.current.setFilter('category', 'CORE_STRATEGY');
    });

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filters.q).toBe('');
    expect(result.current.filters.category).toBe('all');
  });

  test('reads initial filters from URL', () => {
    window.history.pushState({}, '', '?q=Pandemic&category=COOP_ADVENTURE');

    const { result } = renderHook(() => useGameFilters(), { wrapper });

    expect(result.current.filters.q).toBe('Pandemic');
    expect(result.current.filters.category).toBe('COOP_ADVENTURE');
  });
});
```

### 2. Page Component Tests (HIGH PRIORITY)

#### Template: `pages/__tests__/PublicCatalogue.test.jsx`
```javascript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import PublicCatalogue from '../PublicCatalogue';
import * as apiClient from '../../api/client';

// Mock API client
jest.mock('../../api/client');

const mockGames = {
  items: [
    {
      id: 1,
      title: 'Catan',
      category: 'GATEWAY_STRATEGY',
      players_min: 3,
      players_max: 4,
      thumbnail_url: 'http://example.com/catan.jpg',
    },
    {
      id: 2,
      title: 'Pandemic',
      category: 'COOP_ADVENTURE',
      players_min: 2,
      players_max: 4,
      thumbnail_url: 'http://example.com/pandemic.jpg',
    },
  ],
  total: 2,
  page: 1,
  page_size: 12,
};

describe('PublicCatalogue Page', () => {
  beforeEach(() => {
    apiClient.getPublicGames.mockResolvedValue({ data: mockGames });
    apiClient.getPublicCategoryCounts.mockResolvedValue({
      data: {
        GATEWAY_STRATEGY: 50,
        COOP_ADVENTURE: 30,
        CORE_STRATEGY: 40,
        KIDS_FAMILIES: 25,
        PARTY_ICEBREAKERS: 20,
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    expect(screen.getAllByTestId('skeleton-loader')).toHaveLength(12);
  });

  test('renders games after loading', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
      expect(screen.getByText('Pandemic')).toBeInTheDocument();
    });
  });

  test('filters games by search query', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    // Type in search box
    const searchBox = screen.getByPlaceholderText(/search/i);
    await user.type(searchBox, 'Pandemic');

    // Should call API with search query (debounced)
    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalledWith(
        expect.objectContaining({ q: 'Pandemic' })
      );
    });
  });

  test('filters games by category', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    // Click category button
    const categoryButton = screen.getByText(/Gateway Strategy/i);
    await user.click(categoryButton);

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'GATEWAY_STRATEGY' })
      );
    });
  });

  test('handles API errors gracefully', async () => {
    apiClient.getPublicGames.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  test('displays empty state when no games found', async () => {
    apiClient.getPublicGames.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 12 },
    });

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no games found/i)).toBeInTheDocument();
    });
  });
});
```

### 3. API Client Tests (HIGH PRIORITY)

#### Template: `api/__tests__/client.test.js`
```javascript
import axios from 'axios';
import {
  getPublicGames,
  getGameById,
  adminLogin,
  validateAdminToken,
  createGame,
} from '../client';

jest.mock('axios');

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getPublicGames', () => {
    test('fetches games successfully', async () => {
      const mockResponse = {
        data: {
          items: [{ id: 1, title: 'Catan' }],
          total: 1,
        },
      };
      axios.get.mockResolvedValue(mockResponse);

      const result = await getPublicGames({ q: 'Catan' });

      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/public/games'),
        expect.objectContaining({
          params: expect.objectContaining({ q: 'Catan' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    test('handles errors', async () => {
      axios.get.mockRejectedValue(new Error('Network error'));

      await expect(getPublicGames()).rejects.toThrow('Network error');
    });
  });

  describe('getGameById', () => {
    test('fetches single game successfully', async () => {
      const mockGame = { id: 1, title: 'Catan' };
      axios.get.mockResolvedValue({ data: mockGame });

      const result = await getGameById(1);

      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/public/games/1')
      );
      expect(result.data).toEqual(mockGame);
    });
  });

  describe('adminLogin', () => {
    test('logs in successfully', async () => {
      const mockResponse = {
        data: { token: 'test-token', success: true },
      };
      axios.post.mockResolvedValue(mockResponse);

      const result = await adminLogin('admin-token');

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/admin/login'),
        { token: 'admin-token' }
      );
      expect(result.data.token).toBe('test-token');
    });

    test('handles login failure', async () => {
      axios.post.mockRejectedValue({
        response: { status: 401, data: { detail: 'Invalid credentials' } },
      });

      await expect(adminLogin('bad-token')).rejects.toThrow();
    });
  });

  describe('createGame', () => {
    test('requires authentication', async () => {
      const mockGame = { title: 'New Game' };

      await createGame(mockGame, 'auth-token');

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/admin/games'),
        mockGame,
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Admin-Token': 'auth-token',
          }),
        })
      );
    });

    test('handles creation errors', async () => {
      axios.post.mockRejectedValue({
        response: { status: 400, data: { detail: 'Validation error' } },
      });

      await expect(createGame({}, 'token')).rejects.toThrow();
    });
  });
});
```

## Running Tests

### Run All Tests
```bash
cd frontend
npm test
```

### Run with Coverage
```bash
npm test -- --coverage
```

### Run Specific Test File
```bash
npm test -- hooks/__tests__/useAuth.test.js
```

### Watch Mode
```bash
npm test -- --watch
```

## Test Coverage Goals

Target coverage by file type:
- **Hooks**: 90%+ (critical business logic)
- **Pages**: 80%+ (user-facing components)
- **API Client**: 95%+ (critical infrastructure)
- **Components**: 75%+ (UI components)
- **Utils**: 85%+ (helper functions)

## Best Practices

### 1. Test User Behavior, Not Implementation
```javascript
// ❌ Bad: Testing implementation details
test('sets state correctly', () => {
  const { result } = renderHook(() => useState(0));
  expect(result.current[0]).toBe(0);
});

// ✅ Good: Testing user-observable behavior
test('displays count after clicking button', async () => {
  render(<Counter />);
  await userEvent.click(screen.getByRole('button'));
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});
```

### 2. Use Meaningful Test Names
```javascript
// ❌ Bad
test('it works', () => { ... });

// ✅ Good
test('displays error message when API request fails', () => { ... });
```

### 3. Arrange-Act-Assert Pattern
```javascript
test('filters games by category', async () => {
  // Arrange
  render(<PublicCatalogue />);
  const categoryButton = screen.getByText('Strategy');

  // Act
  await userEvent.click(categoryButton);

  // Assert
  expect(apiClient.getPublicGames).toHaveBeenCalledWith(
    expect.objectContaining({ category: 'STRATEGY' })
  );
});
```

### 4. Mock External Dependencies
```javascript
// Mock API calls
jest.mock('../api/client');

// Mock React Router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));
```

### 5. Clean Up After Tests
```javascript
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

afterEach(() => {
  jest.restoreAllMocks();
});
```

## Accessibility Testing

### Test Keyboard Navigation
```javascript
test('can navigate with keyboard', async () => {
  render(<GameCard />);
  const link = screen.getByRole('link');

  link.focus();
  expect(link).toHaveFocus();

  await userEvent.keyboard('{Enter}');
  expect(mockNavigate).toHaveBeenCalled();
});
```

### Test Screen Reader Support
```javascript
test('has proper ARIA labels', () => {
  render(<SearchBox />);
  const input = screen.getByRole('searchbox');

  expect(input).toHaveAccessibleName('Search games');
  expect(input).toHaveAttribute('aria-label');
});
```

## Next Steps

1. **Create test files** for hooks, pages, and API client using templates above
2. **Run tests** to establish baseline: `npm test -- --coverage`
3. **Iteratively improve** coverage to 80%+
4. **Add to CI/CD** in GitHub Actions
5. **Monitor coverage** with Codecov

## Resources

- [React Testing Library Docs](https://testing-library.com/react)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [Common Testing Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
