import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CategorySelectModal from '../CategorySelectModal';

describe('CategorySelectModal', () => {
  const mockOnSelect = vi.fn();
  const mockOnClose = vi.fn();
  const gameTitle = 'Pandemic';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open is true', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    expect(
      screen.getByText(`Select Category for "${gameTitle}"`)
    ).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    render(
      <CategorySelectModal
        open={false}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    expect(
      screen.queryByText(`Select Category for "${gameTitle}"`)
    ).not.toBeInTheDocument();
  });

  it('displays game title in modal heading', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle="Catan"
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText(/Select Category for "Catan"/i)).toBeInTheDocument();
  });

  it('renders all category options', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Co-op & Adventure')).toBeInTheDocument();
    expect(screen.getByText('Gateway Strategy')).toBeInTheDocument();
    expect(screen.getByText('Core Strategy & Epics')).toBeInTheDocument();
    expect(screen.getByText('Kids & Families')).toBeInTheDocument();
    expect(screen.getByText('Party & Icebreakers')).toBeInTheDocument();
  });

  it('calls onSelect when clicking a category', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const coopButton = screen.getByRole('button', {
      name: /Assign to Co-op & Adventure category/i,
    });
    fireEvent.click(coopButton);

    expect(mockOnSelect).toHaveBeenCalledTimes(1);
    expect(mockOnSelect).toHaveBeenCalledWith('COOP_ADVENTURE');
  });

  it('calls onClose when clicking cancel button', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const cancelButton = screen.getByRole('button', {
      name: /Cancel and close dialog/i,
    });
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when pressing Escape key', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when clicking backdrop', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const backdrop = screen.getByRole('dialog');
    fireEvent.click(backdrop);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('does not close when clicking modal content', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const modalContent = screen.getByRole('document');
    fireEvent.click(modalContent);

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('has correct role attributes for accessibility', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
  });

  it('has correct document role for modal content', () => {
    render(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    const document = screen.getByRole('document');
    expect(document).toBeInTheDocument();
  });

  it('focuses first button when modal opens', async () => {
    const { rerender } = render(
      <CategorySelectModal
        open={false}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    rerender(
      <CategorySelectModal
        open={true}
        gameTitle={gameTitle}
        onSelect={mockOnSelect}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      const firstButton = screen.getByRole('button', {
        name: /Assign to Co-op & Adventure category/i,
      });
      expect(document.activeElement).toBe(firstButton);
    });
  });
});
