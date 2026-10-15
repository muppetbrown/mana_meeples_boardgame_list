// src/context/StaffContext.jsx
/**
 * StaffContext - Centralized state management for staff/admin interface
 * Eliminates prop drilling and consolidates business logic
 */
import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';
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
import { parseBggId } from '../utils/bgg';
import ConfirmDialog from '../components/common/ConfirmDialog';

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
  // Optional data-quality filter applied in Manage Library (set from the Dashboard)
  const [attentionFilter, setAttentionFilter] = useState('');

  // Bulk operation state
  const [csvImportText, setCsvImportText] = useState('');
  const [csvCategorizeText, setCsvCategorizeText] = useState('');

  // BGG import state
  const [bggIdInput, setBggIdInput] = useState('');
  const [isAddingGame, setIsAddingGame] = useState(false);

  // Last bulk operation results (shown inline in the bulk panels)
  const [bulkImportResult, setBulkImportResult] = useState(null);
  const [bulkCategorizeResult, setBulkCategorizeResult] = useState(null);
  const [isBulkRunning, setIsBulkRunning] = useState(false);

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
   * Fire-and-forget background operations (CSV import, re-import selected, sleeve
   * fetch, etc.) have no server-side job status to poll. This just tracks what was
   * kicked off and when, so the Dashboard can show "what's in flight" instead of
   * staff having to guess whether something finished.
   */
  const [recentOperations, setRecentOperations] = useState([]);
  const addRecentOperation = useCallback(({ label, etaMs = 60000 }) => {
    const entry = { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, label, startedAt: Date.now(), etaMs };
    setRecentOperations((prev) => [entry, ...prev].slice(0, 8));
    return entry.id;
  }, []);
  const dismissRecentOperation = useCallback((id) => {
    setRecentOperations((prev) => prev.filter((op) => op.id !== id));
  }, []);

  /**
   * Show toast notification
   */
  const toastTimer = useRef(null);
  const showToast = useCallback((message, type = 'info', ms = 2000) => {
    // Clear any pending timer so an older toast can't wipe a newer one
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    // Errors/warnings stay a little longer so they can be read
    const duration = type === 'error' ? Math.max(ms, 4000) : ms;
    toastTimer.current = setTimeout(() => setToast({ message: '', type: 'info' }), duration);
  }, []);

  useEffect(() => () => toastTimer.current && clearTimeout(toastTimer.current), []);

  /**
   * Promise-based confirmation dialog (replaces window.confirm).
   * confirm({ title, message, confirmLabel, tone, requireText }) -> Promise<boolean>
   */
  const [confirmState, setConfirmState] = useState(null);
  const confirm = useCallback(
    (options) =>
      new Promise((resolve) => {
        setConfirmState({ ...options, resolve });
      }),
    []
  );
  const settleConfirm = useCallback((result) => {
    setConfirmState((cur) => {
      cur?.resolve(result);
      return null;
    });
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
   * Derived state - owned games only (buy list / wishlist are managed elsewhere)
   */
  const ownedLibrary = useMemo(
    () => library.filter((g) => !g.status || g.status === 'OWNED'),
    [library]
  );

  /**
   * Derived state - stats
   */
  const stats = useMemo(() => {
    const total = ownedLibrary.length;
    const rated = ownedLibrary.filter((g) => typeof g.average_rating === 'number' && g.average_rating > 0);
    const avg =
      rated.length > 0
        ? (rated.reduce((s, g) => s + g.average_rating, 0) / rated.length).toFixed(1)
        : 'N/A';
    return { total, avgRating: avg };
  }, [ownedLibrary]);

  /**
   * Derived state - category counts (owned games only, matching the lists)
   */
  const counts = useMemo(() => computeCounts(ownedLibrary), [ownedLibrary]);

  /**
   * Derived state - filtered library
   */
  const filteredLibrary = useMemo(() => {
    const ownedGames = ownedLibrary;

    // Then filter by category
    if (selectedCategory === 'all') return ownedGames;
    if (selectedCategory === 'uncategorized')
      return ownedGames.filter((g) => !g.mana_meeple_category);
    return ownedGames.filter((g) => g.mana_meeple_category === selectedCategory);
  }, [ownedLibrary, selectedCategory]);

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
          return true; // Success - exit retry loop
        } catch (error) {
          // Check if it's an HTTP error with response
          const status = error.response?.status;
          const errorMessage = error.response?.data?.detail || error.message;

          // Don't retry on 4xx errors (client errors) except rate limiting
          if (status && status >= 400 && status < 500 && status !== 429) {
            showToast(`Failed to add game: ${errorMessage}`, 'error', 4000);
            return false; // Exit - client error won't be fixed by retry
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
      return false;
    },
    [loadLibrary, showToast]
  );

  /**
   * Handle add game button
   */
  const handleAddGame = useCallback(async () => {
    if (isAddingGame) return;
    // Accept a pasted BGG URL as well as a bare ID
    const id = parseBggId(bggIdInput);
    if (!id) {
      showToast('Please enter a valid BGG ID', 'error');
      return;
    }
    const existing = library.find((g) => g.bgg_id === id);
    if (existing) {
      showToast(`"${existing.title}" is already in your library`, 'warning', 4000);
      return;
    }
    setIsAddingGame(true);
    try {
      // Keep the input until the import succeeds so a failure can be retried
      const ok = await addGameByBggId(id);
      if (ok) setBggIdInput('');
    } finally {
      setIsAddingGame(false);
    }
  }, [bggIdInput, addGameByBggId, library, showToast, isAddingGame]);

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
      if (!csvImportText.trim() || isBulkRunning) return;
      setIsBulkRunning(true);
      try {
        const result = await bulkImportCsv(csvImportText);
        // The server imports in the background, so report what was actually queued
        setBulkImportResult({
          message: result?.message || 'Import started',
          count: result?.count,
          at: new Date(),
        });
        showToast(result?.message || 'Import started in the background', 'success', 4000);
        const count = result?.count || 1;
        addRecentOperation({
          label: `Bulk import (${count} game${count === 1 ? '' : 's'})`,
          etaMs: Math.max(30000, count * 8000),
        });
        setCsvImportText('');
      } catch (e) {
        showToast(e.response?.data?.detail || 'Bulk import failed', 'error');
      } finally {
        setIsBulkRunning(false);
      }
    },
    [csvImportText, showToast, isBulkRunning, addRecentOperation]
  );

  /**
   * Bulk categorize from CSV
   */
  const doBulkCategorize = useCallback(
    async () => {
      if (!csvCategorizeText.trim() || isBulkRunning) return;
      setIsBulkRunning(true);
      try {
        const result = await bulkCategorizeCsv(csvCategorizeText);
        setBulkCategorizeResult({
          updated: result?.updated || [],
          not_found: result?.not_found || [],
          errors: result?.errors || [],
          at: new Date(),
        });
        const u = result?.updated?.length || 0;
        const problems = (result?.not_found?.length || 0) + (result?.errors?.length || 0);
        showToast(
          `Categorized ${u} game(s)${problems ? `, ${problems} need attention` : ''}`,
          problems ? 'warning' : 'success',
          4000
        );
        await loadLibrary();
        setCsvCategorizeText('');
      } catch (e) {
        showToast(e.response?.data?.detail || 'Bulk categorize failed', 'error');
      } finally {
        setIsBulkRunning(false);
      }
    },
    [csvCategorizeText, loadLibrary, showToast, isBulkRunning]
  );

  /**
   * Update a game
   */
  const updateGameData = useCallback(
    async (gameId, updates) => {
      try {
        const updated = await updateGame(gameId, updates);
        if (updated && typeof updated === 'object' && updated.id === gameId) {
          // Patch in place - avoids re-downloading the whole library per edit
          setLibrary((prev) => prev.map((g) => (g.id === gameId ? { ...g, ...updated } : g)));
        } else {
          await loadLibrary();
        }
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
        setLibrary((prev) => prev.filter((g) => g.id !== gameId));
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
    attentionFilter,
    setAttentionFilter,
    csvImportText,
    setCsvImportText,
    csvCategorizeText,
    setCsvCategorizeText,
    bggIdInput,
    setBggIdInput,
    isAddingGame,
    bulkImportResult,
    bulkCategorizeResult,
    isBulkRunning,
    ownedLibrary,
    confirm,
    toast,
    modalOpen,
    pendingGame,
    modalMode,
    isLoading,
    error,
    recentOperations,
    addRecentOperation,
    dismissRecentOperation,

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

  return (
    <StaffContext.Provider value={value}>
      {children}
      {confirmState && (
        <ConfirmDialog
          title={confirmState.title}
          message={confirmState.message}
          confirmLabel={confirmState.confirmLabel}
          tone={confirmState.tone}
          requireText={confirmState.requireText}
          onConfirm={() => settleConfirm(true)}
          onCancel={() => settleConfirm(false)}
        />
      )}
    </StaffContext.Provider>
  );
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

/**
 * Hook returning an async confirm(options) -> boolean.
 * Uses the in-app dialog inside StaffProvider; falls back to window.confirm
 * when rendered standalone (e.g. isolated component tests).
 */
export function useConfirm() {
  const context = useContext(StaffContext);
  if (context?.confirm) return context.confirm;
  return async (options = {}) =>
    window.confirm([options.title, options.message].filter(Boolean).join('\n\n'));
}
