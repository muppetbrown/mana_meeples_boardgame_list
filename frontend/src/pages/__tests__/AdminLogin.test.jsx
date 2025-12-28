// frontend/src/pages/__tests__/AdminLogin.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AdminLogin from '../AdminLogin';
import * as apiClient from '../../api/client';

// Mock API client
vi.mock('../../api/client');

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AdminLogin Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders login form', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /staff login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/admin token/i)).toBeInTheDocument();
  });

  test('validates minimum token length', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'short');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/token must be at least 10 characters/i)).toBeInTheDocument();
    });

    expect(apiClient.adminLogin).not.toHaveBeenCalled();
  });

  test('logs in successfully with valid token', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockResolvedValue({ success: true, token: 'jwt-token' });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'valid-admin-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.adminLogin).toHaveBeenCalledWith('valid-admin-token-123');
      expect(mockNavigate).toHaveBeenCalledWith('/staff');
    });
  });

  test('displays error for invalid token', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid credentials' } },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'invalid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid admin token/i)).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
