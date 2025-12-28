// frontend/src/pages/__tests__/StaffView.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import StaffView from '../StaffView';
import * as apiClient from '../../api/client';

// Mock API client
jest.mock('../../api/client');

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock StaffContext
const mockStaffContext = {
  isValidating: false,
  toast: { message: '', type: 'info' },
  modalOpen: false,
  pendingGame: null,
  stats: {
    total: 100,
    categorized: 80,
    uncategorized: 20,
    byCategory: {},
  },
  handleModalSelect: jest.fn(),
  handleModalClose: jest.fn(),
  refreshGames: jest.fn(),
  showToast: jest.fn(),
};

jest.mock('../../context/StaffContext', () => ({
  StaffProvider: ({ children }) => children,
  useStaff: () => mockStaffContext,
}));

// Mock all tab components
jest.mock('../../components/staff/tabs/DashboardTab', () => ({
  DashboardTab: () => <div>Dashboard Tab</div>,
}));

jest.mock('../../components/staff/tabs/AddGamesTab', () => ({
  AddGamesTab: () => <div>Add Games Tab</div>,
}));

jest.mock('../../components/staff/tabs/ManageLibraryTab', () => ({
  ManageLibraryTab: () => <div>Manage Library Tab</div>,
}));

jest.mock('../../components/staff/tabs/CategoriesTab', () => ({
  CategoriesTab: () => <div>Categories Tab</div>,
}));

jest.mock('../../components/staff/tabs/AdvancedToolsTab', () => ({
  AdvancedToolsTab: () => <div>Advanced Tools Tab</div>,
}));

jest.mock('../../components/staff/tabs/BuyListTab', () => ({
  BuyListTab: () => <div>Buy List Tab</div>,
}));

describe('StaffView Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.confirm = jest.fn(() => true);
  });

  test('renders loading state when validating', () => {
    const validatingContext = { ...mockStaffContext, isValidating: true };
    jest.spyOn(require('../../context/StaffContext'), 'useStaff').mockReturnValue(validatingContext);

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText(/validating credentials/i)).toBeInTheDocument();
  });

  test('renders dashboard tab by default', async () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard Tab')).toBeInTheDocument();
    });
  });

  test('renders tab navigation', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText(/Dashboard/)).toBeInTheDocument();
    expect(screen.getByText(/Add Games/)).toBeInTheDocument();
    expect(screen.getByText(/Manage Library/)).toBeInTheDocument();
    expect(screen.getByText(/Categories/)).toBeInTheDocument();
  });

  test('switches to Add Games tab when clicked', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const addGamesTab = screen.getByText(/Add Games/);
    await user.click(addGamesTab);

    await waitFor(() => {
      expect(screen.getByText('Add Games Tab')).toBeInTheDocument();
    });
  });

  test('switches to Manage Library tab when clicked', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const manageLibraryTab = screen.getByText(/Manage Library/);
    await user.click(manageLibraryTab);

    await waitFor(() => {
      expect(screen.getByText('Manage Library Tab')).toBeInTheDocument();
    });
  });

  test('switches to Categories tab when clicked', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const categoriesTab = screen.getByText(/Categories/);
    await user.click(categoriesTab);

    await waitFor(() => {
      expect(screen.getByText('Categories Tab')).toBeInTheDocument();
    });
  });

  test('updates URL when switching tabs', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const addGamesTab = screen.getByText(/Add Games/);
    await user.click(addGamesTab);

    await waitFor(() => {
      expect(window.location.search).toContain('tab=add-games');
    });
  });

  test('reads active tab from URL on mount', () => {
    window.history.pushState({}, '', '/staff?tab=categories');

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText('Categories Tab')).toBeInTheDocument();
  });

  test('handles logout successfully', async () => {
    const user = userEvent.setup();
    apiClient.adminLogout.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to logout?');
      expect(apiClient.adminLogout).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/staff/login');
    });
  });

  test('handles logout cancellation', async () => {
    const user = userEvent.setup();
    window.confirm = jest.fn(() => false);

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await user.click(logoutButton);

    expect(apiClient.adminLogout).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('navigates to login even if logout API fails', async () => {
    const user = userEvent.setup();
    apiClient.adminLogout.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/staff/login');
    });
  });

  test('renders public library link', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    const publicLibraryLink = screen.getByRole('link', { name: /public library/i });
    expect(publicLibraryLink).toHaveAttribute('href', '/');
  });
});
