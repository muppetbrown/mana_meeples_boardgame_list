// frontend/src/pages/__tests__/AdminLogin.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AdminLogin from '../AdminLogin';
import * as apiClient from '../../api/client';

// Mock API client
jest.mock('../../api/client');

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('AdminLogin Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login form', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /staff login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/admin token/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  test('accepts token input', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    await user.type(tokenInput, 'test-admin-token-123');

    expect(tokenInput).toHaveValue('test-admin-token-123');
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
    expect(mockNavigate).not.toHaveBeenCalled();
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

  test('displays error for invalid token (401)', async () => {
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

  test('displays error for rate limiting (429)', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 429, data: { detail: 'Too many requests' } },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'valid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/too many attempts/i)).toBeInTheDocument();
    });
  });

  test('displays error for network issues', async () => {
    const user = userEvent.setup();
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
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'valid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  test('displays generic error for unknown failures', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 500 },
    });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, 'valid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/authentication failed/i)).toBeInTheDocument();
    });
  });

  test('clears error on new submission', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockRejectedValueOnce({
      response: { status: 401 },
    }).mockResolvedValueOnce({ success: true });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    // First attempt fails
    await user.type(tokenInput, 'invalid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid admin token/i)).toBeInTheDocument();
    });

    // Second attempt succeeds
    await user.clear(tokenInput);
    await user.type(tokenInput, 'valid-token-123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.queryByText(/invalid admin token/i)).not.toBeInTheDocument();
      expect(mockNavigate).toHaveBeenCalledWith('/staff');
    });
  });

  test('trims whitespace from token', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    await user.type(tokenInput, '  valid-token-123  ');
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.adminLogin).toHaveBeenCalledWith('valid-token-123');
    });
  });

  test('has proper accessibility attributes', () => {
    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);
    expect(tokenInput).toHaveAttribute('type', 'password');
    expect(tokenInput).toHaveAttribute('required');
    expect(tokenInput).toHaveAttribute('autocomplete', 'current-password');
  });

  test('error message has proper ARIA attributes', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockRejectedValue({
      response: { status: 401 },
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
      const errorMessage = screen.getByRole('alert');
      expect(errorMessage).toBeInTheDocument();
      expect(errorMessage).toHaveAttribute('aria-live', 'polite');
    });
  });

  test('form can be submitted with Enter key', async () => {
    const user = userEvent.setup();
    apiClient.adminLogin.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <AdminLogin />
      </BrowserRouter>
    );

    const tokenInput = screen.getByLabelText(/admin token/i);

    await user.type(tokenInput, 'valid-token-123');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(apiClient.adminLogin).toHaveBeenCalledWith('valid-token-123');
      expect(mockNavigate).toHaveBeenCalledWith('/staff');
    });
  });
});
