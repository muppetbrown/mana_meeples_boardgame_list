# Mana & Meeples Board Game Library - Frontend

React 18 frontend for the board game catalogue system. This is the **deployed production frontend** served at [library.manaandmeeples.co.nz](https://library.manaandmeeples.co.nz).

## 🚀 Quick Start

### Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm start
```

Visit `http://localhost:3000` to view the app.

### Environment Configuration

The app connects to the backend API. Configuration is handled automatically:

**Development**: Uses `http://127.0.0.1:8000` (local backend)
**Production**: Uses `REACT_APP_API_BASE` environment variable (set in Render)

## 📁 Project Structure

```
frontend/
├── src/
│   ├── pages/               # Page components
│   │   ├── PublicCatalogue.jsx    # Main game browser
│   │   ├── GameDetails.jsx        # Individual game view
│   │   └── AdminLogin.jsx         # Admin authentication
│   │
│   ├── components/          # Reusable components
│   │   ├── public/          # Public-facing components
│   │   │   ├── GameCardPublic.jsx
│   │   │   ├── Pagination.jsx
│   │   │   ├── SortSelect.jsx
│   │   │   └── SearchBox.jsx
│   │   ├── staff/           # Admin components
│   │   │   ├── LibraryCard.jsx
│   │   │   ├── SearchBGGPanel.jsx
│   │   │   └── BulkPanels.jsx
│   │   ├── CategoryFilter.jsx
│   │   ├── CategorySelectModal.jsx
│   │   ├── ErrorBoundary.jsx
│   │   └── GameImage.jsx
│   │
│   ├── utils/               # Utility functions
│   │   └── api.js           # API communication utilities
│   │
│   ├── api/                 # API client
│   │   └── client.js        # API communication layer
│   │
│   ├── constants/           # App constants
│   │   └── categories.js    # Category definitions
│   │
│   ├── App.js               # Main app component & router
│   └── index.js             # App entry point
│
├── public/                  # Static assets
├── build/                   # Production build (generated)
├── package.json
└── tailwind.config.js       # Tailwind CSS configuration
```

## 🛠️ Available Scripts

### `npm start`
Runs the app in development mode at `http://localhost:3000`.

### `npm test`
Launches the test runner in interactive watch mode.

### `npm run build`
Builds the app for production to the `build` folder.
- Optimized and minified
- Includes content hashes for caching
- Ready for deployment

### `npm run eject`
⚠️ **One-way operation** - Ejects from Create React App for full configuration control.

## 🎨 Styling

**Framework**: Tailwind CSS
**Configuration**: `tailwind.config.js`
**PostCSS**: `postcss.config.js`

### Key Design Patterns
- Responsive mobile-first design
- Touch-friendly 44px minimum targets
- Accessible color contrast (WCAG AAA)
- Consistent spacing and typography

## 🔑 Key Features

### Public Catalogue
- Advanced filtering (category, designer, NZ designer, players)
- Full-text search across titles, designers, and descriptions
- Multiple sort options (title, year, rating, playtime)
- Responsive pagination
- URL state persistence for shareable links

### Admin Interface
- Secure session-based authentication
- Game CRUD operations
- BGG import integration
- Bulk operations (CSV import, categorization)
- Category management

### Image Handling
- Progressive loading with opacity transitions
- Automatic fallback to placeholder
- Lazy loading support
- BGG image quality optimization

### Error Handling
- Production-ready error boundaries
- Graceful fallback UI
- Development debugging mode
- User-friendly error messages

## 🚢 Deployment

**Platform**: Render.com static site
**URL**: https://library.manaandmeeples.co.nz
**Auto-deploy**: Enabled from Git repository

### Deployment Process
1. Push changes to main branch
2. Render detects changes
3. Runs `npm run build`
4. Deploys static files
5. Live in ~2-3 minutes

### Environment Variables (Set in Render)
```
REACT_APP_API_BASE=https://mana-meeples-boardgame-list.onrender.com
```

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage
```

## 📱 Browser Support

- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🔗 Related Documentation

- **[Project README](../README.md)** - Main project overview
- **[CLAUDE.md](../CLAUDE.md)** - Complete architecture documentation
- **[Frontend Architecture](../docs/refactoring/REFACTORING_PLAN.md)** - Phase 3 frontend refactoring plan

## 📦 Dependencies

**Core:**
- React 18.x
- React Router v7
- Tailwind CSS

**Utilities:**
- DOMPurify (XSS protection)
- Axios (API communication)

See `package.json` for complete dependency list.

## 🐛 Known Issues

- Category filtering should use API integration (not client-side)

See [Refactoring Plan](../docs/refactoring/REFACTORING_PLAN.md) for planned improvements.

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test locally (`npm start`)
4. Commit with descriptive message
5. Push and create PR
6. Auto-deploy to preview environment

---

Built with ❤️ for Mana & Meeples Café
