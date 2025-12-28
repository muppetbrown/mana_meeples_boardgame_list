// frontend/src/hooks/__tests__/useAuth.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '../useAuth';
import * as apiClient from '../../api/client';

// Mock the API client
vi.mock('../../api/client', () => ({
  adminLogin: vi.fn(),
  validateAdminToken: vi.fn(),
  adminLogout: vi.fn(),
}));

// Mock safeStorage
vi.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
}));

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('initializes with not authenticated state', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
  });

  test('logs in successfully', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockResolvedValue({
      token: 'test-jwt-token',
      success: true
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('test-admin-token');
    });

    expect(loginResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
  });

  test('handles login failure', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValue({
      response: { data: { detail: 'Invalid token' } }
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('bad-token');
    });

    expect(loginResult).toBe(false);
    expect(result.current.error).toBe('Invalid token');
  });

  test('logs out successfully', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockResolvedValue({ success: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    let logoutResult;
    await act(async () => {
      logoutResult = await result.current.logout();
    });

    expect(logoutResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(false);
  });
});
