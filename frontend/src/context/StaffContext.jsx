// src/context/StaffContext.jsx
/**
 * StaffContext - Centralized state management for staff/admin interface
 * Eliminates prop drilling and consolidates business logic
 */
import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getGames,
  bulkImportCsv,
  bulkCategorizeCsv,
  updateGame,
  deleteGame,
  validateAdminToken,
  importFromBGG,
} from '../api/client';
import { CATEGORY_KEYS } from '../constants/categories';

const StaffContext = createContext(null);

/**
 * Helper to compute category counts from library
 */
function computeCounts(list) {
  const counts = { all: list.length, uncategorized: 0 };
  CATEGORY_KEYS.forEach((k) => (counts[k] = 0));
  for (const g of list) {
    const k = g.mana_meeple_category;
    if (!k) counts.uncategorized++;
    else if (Object.prototype.hasOwnProperty.call(counts, k)) counts[k]++;
  }
  return counts;
}

/**
 * StaffProvider - Wraps staff interface with shared state
 */
export function StaffProvider({ children }) {
  const navigate = useNavigate();
  const [isValidating, setIsValidating] = useState(true);

  // Library state
  const [library, setLibrary] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Bulk operation state
  const [csvImportText, setCsvImportText] = useState('');
  const [csvCategorizeText, setCsvCategorizeText] = useState('');

  // BGG import state
  const [bggIdInput, setBggIdInput] = useState('');

  // Toast notifications
  const [toast, setToast] = useState({ message: '', type: 'info' });

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingGame, setPendingGame] = useState(null);
  const [modalMode, setModalMode] = useState('add'); // 'add' | 'edit'

  // Loading states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Show toast notification
   */
  const showToast = useCallback((message, type = 'info', ms = 2000) => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: '', type: 'info' }), ms);
  }, []);

  /**
   * Validate admin session on mount (cookie-based authentication)
   */
  useEffect(() => {
    const validateToken = async () => {
      try {
        // Validate the session cookie (no localStorage needed for cookie-based auth)
        await validateAdminToken();
        setIsValidating(false);
      } catch (error) {
        // Session is invalid or expired, redirect to login
        navigate('/staff/login');
      }
    };

    validateToken();
  }, [navigate]);

  /**
   * Load library from API
   */
  const loadLibrary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getGames();
      setLibrary(Array.isArray(data) ? data : []);
      if (typeof window !== 'undefined') window.__LIB__ = Array.isArray(data) ? data : [];
    } catch (e) {
      const errorMsg = 'Failed to load library';
      setError(errorMsg);
      showToast(errorMsg, 'error');
      setLibrary([]);
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  /**
   * Load library on mount
   */
  useEffect(() => {
    if (!isValidating) {
      loadLibrary();
    }
  }, [isValidating, loadLibrary]);

  /**
   * Derived state - stats
   */
  const stats = useMemo(() => {
    const total = library.length;
    const available = library.filter((g) => g.available).length;
    const rated = library.filter((g) => typeof g.rating === 'number');
    const avg =
      rated.length > 0
        ? (rated.reduce((s, g) => s + g.rating, 0) / rated.length).toFixed(1)
        : 'N/A';
    return { total, available, avgRating: avg };
  }, [library]);

  /**
   * Derived state - category counts
   */
  const counts = useMemo(() => computeCounts(library), [library]);

  /**
   * Derived state - filtered library
   */
  const filteredLibrary = useMemo(() => {
    if (selectedCategory === 'all') return library;
    if (selectedCategory === 'uncategorized')
      return library.filter((g) => !g.mana_meeple_category);
    return library.filter((g) => g.mana_meeple_category === selectedCategory);
  }, [library, selectedCategory]);

  /**
   * Add game by BGG ID with retry logic
   */
  const addGameByBggId = useCallback(
    async (bggId) => {
      const MAX_RETRIES = 4;
      const RETRY_DELAYS = [2000, 4000, 8000, 16000]; // Exponential backoff in ms

      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        try {
          if (attempt > 0) {
            showToast(`Retrying... (attempt ${attempt + 1}/${MAX_RETRIES + 1})`, 'info', 3000);
          } else {
            showToast(`Adding game from BGG ID ${bggId}...`, 'info', 2000);
          }

          const result = await importFromBGG(bggId);
          showToast(`Added "${result.title}" successfully!`, 'success');
          await loadLibrary();
          return; // Success - exit retry loop
        } catch (error) {
          // Check if it's an HTTP error with response
          const status = error.response?.status;
          const errorMessage = error.response?.data?.detail || error.message;

          // Don't retry on 4xx errors (client errors) except rate limiting
          if (status && status >= 400 && status < 500 && status !== 429) {
            showToast(`Failed to add game: ${errorMessage}`, 'error', 4000);
            return; // Exit - client error won't be fixed by retry
          }

          // For server errors, rate limiting, or network errors, retry if attempts left
          if (attempt < MAX_RETRIES) {
            const delay = RETRY_DELAYS[attempt];
            const errorType = status ? `Server error (${status})` : 'Network error';
            showToast(`${errorType}. Retrying in ${delay / 1000}s...`, 'warning', delay);
            await new Promise((resolve) => setTimeout(resolve, delay));
            continue; // Retry
          } else {
            // Final attempt failed
            const finalMessage = status
              ? `Failed after ${MAX_RETRIES + 1} attempts: ${errorMessage}`
              : `Network error after ${MAX_RETRIES + 1} attempts. Please check your connection.`;
            showToast(finalMessage, 'error', 5000);
          }
        }
      }
    },
    [loadLibrary, showToast]
  );

  /**
   * Handle add game button
   */
  const handleAddGame = useCallback(() => {
    const id = parseInt(bggIdInput.trim());
    if (isNaN(id) || id <= 0) {
      showToast('Please enter a valid BGG ID', 'error');
      return;
    }
    addGameByBggId(id);
    setBggIdInput('');
  }, [bggIdInput, addGameByBggId, showToast]);

  /**
   * Open edit category modal
   */
  const openEditCategory = useCallback((game) => {
    setPendingGame(game);
    setModalMode('edit');
    setModalOpen(true);
  }, []);

  /**
   * Handle modal category selection
   */
  const handleModalSelect = useCallback(
    async (catKey) => {
      setModalOpen(false);
      if (!pendingGame) return;

      try {
        if (modalMode === 'edit') {
          await updateGame(pendingGame.id, { mana_meeple_category: catKey });
          showToast(`Updated to category`, 'success');
          await loadLibrary();
        }
      } catch {
        showToast('Action failed', 'error');
      } finally {
        setPendingGame(null);
      }
    },
    [pendingGame, modalMode, loadLibrary, showToast]
  );

  /**
   * Close modal
   */
  const handleModalClose = useCallback(() => {
    setModalOpen(false);
    setPendingGame(null);
  }, []);

  /**
   * Bulk import from CSV
   */
  const doBulkImport = useCallback(
    async () => {
      if (!csvImportText.trim()) return;
      try {
        await bulkImportCsv(csvImportText);
        showToast('Import finished', 'success');
        await loadLibrary();
        setCsvImportText('');
      } catch (e) {
        showToast('Bulk import failed', 'error');
      }
    },
    [csvImportText, loadLibrary, showToast]
  );

  /**
   * Bulk categorize from CSV
   */
  const doBulkCategorize = useCallback(
    async () => {
      if (!csvCategorizeText.trim()) return;
      try {
        await bulkCategorizeCsv(csvCategorizeText);
        showToast('Categorization finished', 'success');
        await loadLibrary();
        setCsvCategorizeText('');
      } catch (e) {
        showToast('Bulk categorize failed', 'error');
      }
    },
    [csvCategorizeText, loadLibrary, showToast]
  );

  /**
   * Update a game
   */
  const updateGameData = useCallback(
    async (gameId, updates) => {
      try {
        await updateGame(gameId, updates);
        await loadLibrary();
        showToast('Game updated', 'success');
      } catch (e) {
        showToast('Failed to update game', 'error');
        throw e;
      }
    },
    [loadLibrary, showToast]
  );

  /**
   * Delete a game
   */
  const deleteGameData = useCallback(
    async (gameId) => {
      try {
        await deleteGame(gameId);
        await loadLibrary();
        showToast('Game deleted', 'success');
      } catch (e) {
        showToast('Failed to delete game', 'error');
        throw e;
      }
    },
    [loadLibrary, showToast]
  );

  // Context value
  const value = {
    // State
    isValidating,
    library,
    selectedCategory,
    setSelectedCategory,
    csvImportText,
    setCsvImportText,
    csvCategorizeText,
    setCsvCategorizeText,
    bggIdInput,
    setBggIdInput,
    toast,
    modalOpen,
    pendingGame,
    modalMode,
    isLoading,
    error,

    // Derived state
    stats,
    counts,
    filteredLibrary,

    // Actions
    loadLibrary,
    addGameByBggId,
    handleAddGame,
    openEditCategory,
    handleModalSelect,
    handleModalClose,
    doBulkImport,
    doBulkCategorize,
    updateGameData,
    deleteGameData,
    showToast,
  };

  return <StaffContext.Provider value={value}>{children}</StaffContext.Provider>;
}

/**
 * Hook to use staff context
 */
export function useStaff() {
  const context = useContext(StaffContext);
  if (!context) {
    throw new Error('useStaff must be used within StaffProvider');
  }
  return context;
}
