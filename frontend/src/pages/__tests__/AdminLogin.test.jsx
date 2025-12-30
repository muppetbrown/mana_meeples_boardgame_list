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
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'short');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/token must be at least 10 characters/i)).toBeInTheDocument();
    });

    expect(apiClient.adminLogin).not.toHaveBeenCalled();
  });

  test('logs in successfully with valid token', async () => {
    apiClient.adminLogin.mockResolvedValue({ success: true, token: 'jwt-token' });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'valid-admin-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(apiClient.adminLogin).toHaveBeenCalledWith('valid-admin-token-123');
      expect(mockNavigate).toHaveBeenCalledWith('/staff');
    });
  });

  test('displays error for invalid token', async () => {
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid credentials' } },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'invalid-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid admin token/i)).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('displays rate limit error (429)', async () => {
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 429, data: { detail: 'Too many requests' } },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'valid-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/too many attempts/i)).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('displays network error', async () => {
    apiClient.adminLogin.mockRejectedValue({
      message: 'Network Error',
      code: 'ERR_NETWORK',
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'valid-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('displays generic error for unknown errors', async () => {
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 500 },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'valid-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/authentication failed/i)).toBeInTheDocument();
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('submit button is disabled when token is empty', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    expect(submitButton).toBeDisabled();
  });

  test('submit button is disabled when token is whitespace', async () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, '   ');

    expect(submitButton).toBeDisabled();
  });

  test('submit button is enabled when token is valid', async () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'some-token');

    expect(submitButton).not.toBeDisabled();
  });

  test('navigates back when back button clicked', async () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const backButton = screen.getByRole('button', { name: /back to games/i });
    await userEvent.click(backButton);

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  test('updates token input when typing', async () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    await userEvent.type(tokenInput, 'test-token-123');

    expect(tokenInput).toHaveValue('test-token-123');
  });

  test('clears error when submitting again', async () => {
    apiClient.adminLogin
      .mockRejectedValueOnce({
        response: { status: 401, data: { detail: 'Invalid' } },
      })
      .mockResolvedValueOnce({ success: true, token: 'jwt-token' });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    // First attempt - error
    await userEvent.type(tokenInput, 'invalid-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid admin token/i)).toBeInTheDocument();
    });

    // Second attempt - should clear error
    await userEvent.clear(tokenInput);
    await userEvent.type(tokenInput, 'valid-token-456');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.queryByText(/invalid admin token/i)).not.toBeInTheDocument();
      expect(mockNavigate).toHaveBeenCalledWith('/staff');
    });
  });

  test('has skip to login form link', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const skipLink = screen.getByText(/skip to login form/i);
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute('href', '#login-form');
  });

  test('error message has proper ARIA attributes', async () => {
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid' } },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, 'invalid-token-123');
    await userEvent.click(submitButton);

    await waitFor(() => {
      const errorMessage = screen.getByRole('alert');
      expect(errorMessage).toBeInTheDocument();
      expect(errorMessage).toHaveAttribute('aria-live', 'polite');
      expect(errorMessage).toHaveAttribute('id', 'login-error');
    });

    // Verify input is connected to error via aria-describedby
    expect(tokenInput).toHaveAttribute('aria-describedby', 'login-error');
  });

  test('form has proper role and accessibility attributes', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const form = screen.getByRole('main');
    expect(form).toHaveAttribute('id', 'login-form');
  });

  test('input has proper autocomplete attribute', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    expect(tokenInput).toHaveAttribute('autocomplete', 'current-password');
  });

  test('input has required attribute', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    expect(tokenInput).toBeRequired();
  });

  test('trims whitespace from token before submission', async () => {
    apiClient.adminLogin.mockResolvedValue({ success: true, token: 'jwt-token' });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(tokenInput, '  valid-token-123  ');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(apiClient.adminLogin).toHaveBeenCalledWith('valid-token-123');
    });
  });

  test('displays descriptive subtitle', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    expect(screen.getByText(/access the admin dashboard/i)).toBeInTheDocument();
  });
});
