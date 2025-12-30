// frontend/src/components/onboarding/__tests__/HelpModal.test.jsx
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HelpModal } from '../HelpModal';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  X: () => <div data-testid="x-icon">X</div>,
}));

describe('HelpModal Component', () => {
  let mockOnClose;

  beforeEach(() => {
    mockOnClose = vi.fn();
    // Reset body overflow before each test
    document.body.style.overflow = '';
  });

  afterEach(() => {
    // Clean up body overflow after each test
    document.body.style.overflow = '';
  });

  describe('Rendering', () => {
    test('renders nothing when isOpen is false', () => {
      const { container } = render(
        <HelpModal isOpen={false} onClose={mockOnClose} />
      );

      expect(container.firstChild).toBeNull();
    });

    test('renders modal when isOpen is true', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Library Guide')).toBeInTheDocument();
    });

    test('has proper ARIA attributes', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'help-modal-title');
    });

    test('displays default "Game Cards" tab content', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/Tap to Expand Cards/i)).toBeInTheDocument();
      expect(screen.getByText(/Player Count/i)).toBeInTheDocument();
    });
  });

  describe('Tab Switching', () => {
    test('switches to AfterGame tab when clicked', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/What is "Plan a Game"\?/i)).toBeInTheDocument();
      });
    });

    test('switches back to Game Cards tab when clicked', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      // Switch to AfterGame tab first
      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/What is "Plan a Game"\?/i)).toBeInTheDocument();
      });

      // Switch back to Game Cards tab
      const gameCardsTab = screen.getByRole('button', { name: /game cards/i });
      fireEvent.click(gameCardsTab);

      await waitFor(() => {
        expect(screen.getByText(/Tap to Expand Cards/i)).toBeInTheDocument();
      });
    });

    test('applies active styles to selected tab', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const gameCardsTab = screen.getByRole('button', { name: /game cards/i });
      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });

      // Game Cards tab should be active by default
      expect(gameCardsTab.className).toContain('border-emerald-600');
      expect(afterGameTab.className).toContain('border-transparent');

      // Switch to AfterGame tab
      fireEvent.click(afterGameTab);

      // AfterGame tab should now be active
      expect(afterGameTab.className).toContain('border-emerald-600');
    });
  });

  describe('Close Functionality', () => {
    test('calls onClose when close button clicked', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const closeButton = screen.getByRole('button', { name: /close help/i });
      fireEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('calls onClose when "Got it, thanks!" button clicked', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const gotItButton = screen.getByRole('button', { name: /got it, thanks!/i });
      fireEvent.click(gotItButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('calls onClose when backdrop clicked', () => {
      const { container } = render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const backdrop = container.querySelector('[aria-hidden="true"]');
      fireEvent.click(backdrop);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('calls onClose when Escape key pressed', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('does not call onClose for other keys', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      fireEvent.keyDown(document, { key: 'Enter' });
      fireEvent.keyDown(document, { key: 'a' });

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    test('does not call onClose when Escape pressed and modal is closed', () => {
      const { rerender } = render(
        <HelpModal isOpen={true} onClose={mockOnClose} />
      );

      // Close the modal
      rerender(<HelpModal isOpen={false} onClose={mockOnClose} />);

      // Try to press Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Body Scroll Lock', () => {
    test('prevents body scroll when modal is open', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(document.body.style.overflow).toBe('hidden');
    });

    test('restores body scroll when modal is closed', () => {
      const { rerender } = render(
        <HelpModal isOpen={true} onClose={mockOnClose} />
      );

      expect(document.body.style.overflow).toBe('hidden');

      rerender(<HelpModal isOpen={false} onClose={mockOnClose} />);

      expect(document.body.style.overflow).toBe('');
    });

    test('restores body scroll on unmount', () => {
      const { unmount } = render(
        <HelpModal isOpen={true} onClose={mockOnClose} />
      );

      expect(document.body.style.overflow).toBe('hidden');

      unmount();

      expect(document.body.style.overflow).toBe('');
    });
  });

  describe('Game Cards Tab Content', () => {
    test('displays card expansion information', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/Tap to Expand Cards/i)).toBeInTheDocument();
      expect(screen.getByText(/Rating & Complexity/i)).toBeInTheDocument();
      expect(screen.getByText(/Designers/i)).toBeInTheDocument();
      expect(screen.getByText(/Description/i)).toBeInTheDocument();
    });

    test('displays icon meanings', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      // Player Count icon info
      const playerCountElements = screen.getAllByText(/Player Count/i);
      expect(playerCountElements.length).toBeGreaterThan(0);

      // Other icon info should be present
      expect(screen.getByText(/Play Time/i)).toBeInTheDocument();
    });

    test('displays category badges information', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/Category Badges/i)).toBeInTheDocument();
      expect(screen.getByText(/Gateway Strategy/i)).toBeInTheDocument();
      expect(screen.getByText(/Kids & Families/i)).toBeInTheDocument();
      expect(screen.getByText(/Core Strategy/i)).toBeInTheDocument();
      expect(screen.getByText(/Co-op & Adventure/i)).toBeInTheDocument();
      expect(screen.getByText(/Party & Icebreakers/i)).toBeInTheDocument();
    });

    test('displays quick tip section', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      expect(screen.getByText(/Quick Tip/i)).toBeInTheDocument();
    });
  });

  describe('AfterGame Tab Content', () => {
    test('displays AfterGame explanation when tab is active', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/What is "Plan a Game"\?/i)).toBeInTheDocument();
        expect(screen.getByText(/How it Works/i)).toBeInTheDocument();
      });
    });

    test('displays scheduling steps', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        // Check for key parts of the scheduling flow
        expect(screen.getByText(/Find a game/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Other steps should also be there
      expect(screen.getByText(/Schedule your session/i)).toBeInTheDocument();
      expect(screen.getByText(/Meet up and play!/i)).toBeInTheDocument();
    });

    test('displays benefits of scheduling', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/Why Schedule Games\?/i)).toBeInTheDocument();
        expect(screen.getByText(/Find players/i)).toBeInTheDocument();
        expect(screen.getByText(/Plan ahead/i)).toBeInTheDocument();
        expect(screen.getByText(/Build community/i)).toBeInTheDocument();
        expect(screen.getByText(/Try new games/i)).toBeInTheDocument();
      });
    });

    test('displays AfterGame platform information', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/About AfterGame/i)).toBeInTheDocument();
        expect(screen.getByText(/Pre-fills the game you selected/i)).toBeInTheDocument();
        expect(screen.getByText(/Sets the location to Mana & Meeples/i)).toBeInTheDocument();
        expect(screen.getByText(/Connects you to our gaming group/i)).toBeInTheDocument();
      });
    });

    test('displays pro tip', async () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const afterGameTab = screen.getByRole('button', { name: /plan a game/i });
      fireEvent.click(afterGameTab);

      await waitFor(() => {
        expect(screen.getByText(/Pro Tip/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    test('close button has proper aria-label', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const closeButton = screen.getByRole('button', { name: /close help/i });
      expect(closeButton).toHaveAttribute('aria-label', 'Close help');
    });

    test('modal title has proper id for aria-labelledby', () => {
      render(<HelpModal isOpen={true} onClose={mockOnClose} />);

      const title = screen.getByText('Library Guide');
      expect(title).toHaveAttribute('id', 'help-modal-title');
    });

    test('backdrop has aria-hidden', () => {
      const { container } = render(
        <HelpModal isOpen={true} onClose={mockOnClose} />
      );

      const backdrop = container.querySelector('[aria-hidden="true"]');
      expect(backdrop).toBeInTheDocument();
    });
  });

  describe('Event Cleanup', () => {
    test('removes escape key listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');

      const { unmount } = render(
        <HelpModal isOpen={true} onClose={mockOnClose} />
      );

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'keydown',
        expect.any(Function)
      );

      removeEventListenerSpy.mockRestore();
    });
  });
});
