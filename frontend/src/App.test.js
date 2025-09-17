import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';

// Mock the API client
jest.mock('./api/client', () => ({
  getPublicGames: jest.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 24
  }),
  getCategoryCounts: jest.fn().mockResolvedValue({}),
  getGame: jest.fn(),
  getGames: jest.fn().mockResolvedValue([]),
  bulkImportCsv: jest.fn(),
  bulkCategorizeCsv: jest.fn(),
  addGame: jest.fn(),
  updateGame: jest.fn(),
  deleteGame: jest.fn(),
}));

// Test helper to render App with Router
const renderApp = () => {
  return render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
};

test('renders public catalogue by default', async () => {
  renderApp();
  
  // Should render the public catalogue page
  await waitFor(() => {
    expect(screen.getByText(/Mana & Meeples/i)).toBeInTheDocument();
  });
});

test('renders app without crashing', () => {
  renderApp();
  // Basic smoke test - app should render without errors
});
