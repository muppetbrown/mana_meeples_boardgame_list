/**
 * Manual mock for react-router-dom
 *
 * React Router v7 is ESM-only and not compatible with Jest's CommonJS environment.
 * This mock provides the essential routing components and hooks needed for testing.
 */

const React = require('react');

module.exports = {
  BrowserRouter: ({ children }) => React.createElement('div', { 'data-testid': 'browser-router' }, children),
  MemoryRouter: ({ children }) => React.createElement('div', { 'data-testid': 'memory-router' }, children),
  Link: ({ children, to, ...props }) => React.createElement('a', { href: to, ...props }, children),
  NavLink: ({ children, to, ...props }) => React.createElement('a', { href: to, ...props }, children),
  useNavigate: () => jest.fn(),
  useParams: () => ({}),
  useLocation: () => ({
    pathname: '/',
    search: '',
    hash: '',
    state: null,
    key: 'default',
  }),
  useSearchParams: () => [new URLSearchParams(), jest.fn()],
  Outlet: () => React.createElement('div', { 'data-testid': 'outlet' }),
};
