// frontend/src/hooks/__tests__/useGameFilters.test.js
import { renderHook, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { useGameFilters } from '../useGameFilters';

const wrapper = ({ children }) => <BrowserRouter>{children}</BrowserRouter>;

describe('useGameFilters Hook', () => {
  beforeEach(() => {
    // Reset URL
    window.history.pushState({}, '', '/');
  });

  test('initializes with default filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    expect(result.current.q).toBe('');
    expect(result.current.category).toBe('all');
    expect(result.current.designer).toBe('');
    expect(result.current.nzDesigner).toBe(false);
    expect(result.current.players).toBe('');
    expect(result.current.recentlyAdded).toBe(false);
    expect(result.current.sort).toBe('year_desc');
  });

  test('initializes with custom default filters', () => {
    const { result } = renderHook(() => useGameFilters({ sort: 'title_asc', category: 'GATEWAY_STRATEGY' }), { wrapper });

    expect(result.current.sort).toBe('title_asc');
    expect(result.current.category).toBe('GATEWAY_STRATEGY');
  });

  test('reads initial filters from URL', () => {
    window.history.pushState({}, '', '?q=Pandemic&category=COOP_ADVENTURE&sort=title_asc');

    const { result } = renderHook(() => useGameFilters(), { wrapper });

    expect(result.current.q).toBe('Pandemic');
    expect(result.current.category).toBe('COOP_ADVENTURE');
    expect(result.current.sort).toBe('title_asc');
  });

  test('updates search query', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateSearch('Catan');
    });

    expect(result.current.q).toBe('Catan');
  });

  test('debounces search query', async () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateSearch('Cat');
    });

    // qDebounced should not update immediately
    expect(result.current.qDebounced).toBe('');

    // Wait for debounce (150ms)
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    expect(result.current.qDebounced).toBe('Cat');
  });

  test('updates category filter', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateCategory('CORE_STRATEGY');
    });

    expect(result.current.category).toBe('CORE_STRATEGY');
  });

  test('updates designer filter', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateDesigner('Reiner Knizia');
    });

    expect(result.current.designer).toBe('Reiner Knizia');
  });

  test('updates NZ designer filter', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateNzDesigner(true);
    });

    expect(result.current.nzDesigner).toBe(true);
  });

  test('updates players filter', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updatePlayers('4');
    });

    expect(result.current.players).toBe('4');
  });

  test('updates recently added filter', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateRecentlyAdded(true);
    });

    expect(result.current.recentlyAdded).toBe(true);
  });

  test('updates sort order', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateSort('rating_desc');
    });

    expect(result.current.sort).toBe('rating_desc');
  });

  test('clears all filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    // Set some filters
    act(() => {
      result.current.updateSearch('Catan');
      result.current.updateCategory('GATEWAY_STRATEGY');
      result.current.updateDesigner('Klaus Teuber');
      result.current.updateNzDesigner(true);
      result.current.updatePlayers('4');
      result.current.updateRecentlyAdded(true);
      result.current.updateSort('title_asc');
    });

    // Clear all filters
    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.q).toBe('');
    expect(result.current.category).toBe('all');
    expect(result.current.designer).toBe('');
    expect(result.current.nzDesigner).toBe(false);
    expect(result.current.players).toBe('');
    expect(result.current.recentlyAdded).toBe(false);
    expect(result.current.sort).toBe('year_desc');
  });

  test('generates filter params for API calls', async () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateSearch('Pandemic');
      result.current.updateCategory('COOP_ADVENTURE');
      result.current.updateDesigner('Matt Leacock');
      result.current.updateNzDesigner(true);
      result.current.updatePlayers('4');
    });

    // Wait for debounce
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    const params = result.current.getFilterParams({ page: 1 });

    expect(params).toEqual({
      q: 'Pandemic',
      sort: 'year_desc',
      category: 'COOP_ADVENTURE',
      designer: 'Matt Leacock',
      nz_designer: true,
      players: 4,
      page: 1,
    });
  });

  test('excludes default values from filter params', async () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    // Wait for debounce
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    const params = result.current.getFilterParams();

    expect(params).toEqual({
      q: '',
      sort: 'year_desc',
    });
    expect(params.category).toBeUndefined();
    expect(params.designer).toBeUndefined();
    expect(params.nz_designer).toBeUndefined();
    expect(params.players).toBeUndefined();
  });

  test('detects active filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    // No filters active initially
    expect(result.current.hasActiveFilters).toBe(false);

    // Add a filter
    act(() => {
      result.current.updateSearch('Catan');
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });

  test('updates URL parameters when filters change', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateCategory('GATEWAY_STRATEGY');
    });

    expect(window.location.search).toContain('category=GATEWAY_STRATEGY');
  });

  test('updates URL with multiple filters', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    act(() => {
      result.current.updateSearch('Pandemic');
      result.current.updateCategory('COOP_ADVENTURE');
      result.current.updateNzDesigner(true);
    });

    const search = window.location.search;
    expect(search).toContain('q=Pandemic');
    expect(search).toContain('category=COOP_ADVENTURE');
    expect(search).toContain('nz_designer=true');
  });

  test('removes filters from URL when cleared', () => {
    const { result } = renderHook(() => useGameFilters(), { wrapper });

    // Set a filter
    act(() => {
      result.current.updateCategory('CORE_STRATEGY');
    });

    expect(window.location.search).toContain('category=CORE_STRATEGY');

    // Clear filters
    act(() => {
      result.current.clearFilters();
    });

    expect(window.location.search).not.toContain('category');
  });
});
