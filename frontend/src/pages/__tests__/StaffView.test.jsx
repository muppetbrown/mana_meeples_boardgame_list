// frontend/src/pages/__tests__/StaffView.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import StaffView from '../StaffView';

vi.mock('../../api/client');

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

  test('renders tab navigation', () => {
    render(
      <BrowserRouter>
        <StaffView />
      </BrowserRouter>
    );

    expect(screen.getByText(/Dashboard/)).toBeInTheDocument();
    expect(screen.getByText(/Add Games/)).toBeInTheDocument();
  });
});
