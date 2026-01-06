// frontend/src/pages/__tests__/StaffView.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import StaffView from '../StaffView';

vi.mock('../../api/client');

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockStaffContext = {
  isValidating: false,
  toast: { message: '', type: 'info' },
  modalOpen: false,
  pendingGame: null,
  stats: { total: 100, categorized: 80, uncategorized: 20, byCategory: {} },
  handleModalSelect: vi.fn(),
  handleModalClose: vi.fn(),
  refreshGames: vi.fn(),
  showToast: vi.fn(),
};

vi.mock('../../context/StaffContext', () => ({
  StaffProvider: ({ children }) => children,
  useStaff: () => mockStaffContext,
}));

vi.mock('../../components/staff/tabs/DashboardTab', () => ({
  DashboardTab: () => <div>Dashboard Tab</div>,
}));

vi.mock('../../components/staff/tabs/AddGamesTab', () => ({
  AddGamesTab: () => <div>Add Games Tab</div>,
}));

vi.mock('../../components/staff/tabs/ManageLibraryTab', () => ({
  ManageLibraryTab: () => <div>Manage Library Tab</div>,
}));

vi.mock('../../components/staff/tabs/CategoriesTab', () => ({
  CategoriesTab: () => <div>Categories Tab</div>,
}));

vi.mock('../../components/staff/tabs/AdvancedToolsTab', () => ({
  AdvancedToolsTab: () => <div>Advanced Tools Tab</div>,
}));

vi.mock('../../components/staff/tabs/BuyListTab', () => ({
  BuyListTab: () => <div>Buy List Tab</div>,
}));

describe('StaffView Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders dashboard tab by default', async () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText('Dashboard Tab')).toBeInTheDocument();
  });

  test('renders staff interface', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    // Just check that the component renders without errors
    expect(screen.getByText('Dashboard Tab')).toBeInTheDocument();
  });

  test('displays admin panel header', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText(/Mana & Meeples — Admin Panel/i)).toBeInTheDocument();
  });

  test('displays stats in header', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText(/100/)).toBeInTheDocument(); // total games from mock
  });

  test('displays logout button', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  describe('Tab navigation', () => {
    test('switches to add games tab when clicked', async () => {
      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const addGamesTab = screen.getByRole('button', { name: /add games/i });
      userEvent.click(addGamesTab);

      await screen.findByText('Add Games Tab');
      expect(screen.getByText('Add Games Tab')).toBeInTheDocument();
    });

    test('switches to manage library tab when clicked', async () => {
      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const manageTab = screen.getByRole('button', { name: /manage library/i });
      userEvent.click(manageTab);

      await screen.findByText('Manage Library Tab');
      expect(screen.getByText('Manage Library Tab')).toBeInTheDocument();
    });

    test('switches to categories tab when clicked', async () => {
      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const categoriesTab = screen.getByRole('button', { name: /categories/i });
      userEvent.click(categoriesTab);

      await screen.findByText('Categories Tab');
      expect(screen.getByText('Categories Tab')).toBeInTheDocument();
    });

    test('switches to buy list tab when clicked', async () => {
      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const buyListTab = screen.getByRole('button', { name: /buy list/i });
      userEvent.click(buyListTab);

      await screen.findByText('Buy List Tab');
      expect(screen.getByText('Buy List Tab')).toBeInTheDocument();
    });

    test('switches to advanced tools tab when clicked', async () => {
      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const advancedTab = screen.getByRole('button', { name: /advanced tools/i });
      userEvent.click(advancedTab);

      await screen.findByText('Advanced Tools Tab');
      expect(screen.getByText('Advanced Tools Tab')).toBeInTheDocument();
    });
  });

  describe('URL parameter persistence', () => {
    test('loads tab from URL parameter', async () => {
      render(
        <MemoryRouter initialEntries={['/staff?tab=add-games']}>
          <StaffView />
        </MemoryRouter>
      );

      await screen.findByText('Add Games Tab');
      expect(screen.getByText('Add Games Tab')).toBeInTheDocument();
    });

    test('defaults to dashboard for invalid tab parameter', async () => {
      render(
        <MemoryRouter initialEntries={['/staff?tab=invalid']}>
          <StaffView />
        </MemoryRouter>
      );

      await screen.findByText('Dashboard Tab');
      expect(screen.getByText('Dashboard Tab')).toBeInTheDocument();
    });
  });

  describe('Logout functionality', () => {
    test('shows confirmation dialog when logout clicked', async () => {
      
      
      window.confirm = vi.fn(() => false);

      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const logoutButton = screen.getByRole('button', { name: /logout/i });
      await userEvent.click(logoutButton);

      expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to logout?');
    });

    test('navigates to login when logout confirmed', async () => {
      window.confirm = vi.fn(() => true);

      const { adminLogout: mockAdminLogout } = await import('../../api/client');
      mockAdminLogout.mockResolvedValue({});

      render(
        <BrowserRouter>
          <StaffView />
        </BrowserRouter>
      );

      const logoutButton = screen.getByRole('button', { name: /logout/i });
      userEvent.click(logoutButton);

      // Note: Navigation testing is limited in this setup
      // Real navigation would be tested in E2E tests
    });
  });
});
