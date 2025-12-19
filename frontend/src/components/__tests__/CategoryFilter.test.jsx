import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CategoryFilter from '../CategoryFilter';

describe('CategoryFilter', () => {
  const mockOnChange = vi.fn();
  const mockCategoryCounts = {
    all: 65,
    COOP_ADVENTURE: 10,
    GATEWAY_STRATEGY: 15,
    CORE_STRATEGY: 20,
    KIDS_FAMILIES: 12,
    PARTY_ICEBREAKERS: 8,
    uncategorized: 3,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all category buttons', () => {
    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    // Check for "All Games" button
    expect(screen.getByText(/All Games/i)).toBeInTheDocument();

    // Check for category labels
    expect(screen.getByText(/Co-op & Adventure/i)).toBeInTheDocument();
    expect(screen.getByText(/Gateway Strategy/i)).toBeInTheDocument();
    expect(screen.getByText(/Core Strategy/i)).toBeInTheDocument();
    expect(screen.getByText(/Kids & Families/i)).toBeInTheDocument();
    expect(screen.getByText(/Party & Icebreakers/i)).toBeInTheDocument();
  });

  it('displays category counts', () => {
    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    // Check counts are displayed
    expect(screen.getByText('65')).toBeInTheDocument(); // all
    expect(screen.getByText('10')).toBeInTheDocument(); // COOP_ADVENTURE
    expect(screen.getByText('15')).toBeInTheDocument(); // GATEWAY_STRATEGY
    expect(screen.getByText('20')).toBeInTheDocument(); // CORE_STRATEGY
  });

  it('calls onChange when clicking a category button', () => {
    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    const coopButton = screen.getByRole('button', {
      name: /Filter by Co-op & Adventure/i,
    });
    fireEvent.click(coopButton);

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith('COOP_ADVENTURE');
  });

  it('highlights the selected category', () => {
    render(
      <CategoryFilter
        selected="GATEWAY_STRATEGY"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    const selectedButton = screen.getByRole('button', {
      name: /Filter by Gateway Strategy/i,
    });

    expect(selectedButton).toHaveClass('bg-purple-600', 'text-white');
    expect(selectedButton).toHaveAttribute('aria-pressed', 'true');
  });

  it('navigates to next category with arrow right', () => {
    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    const allButton = screen.getByRole('button', { name: /Filter by All Games/i });
    fireEvent.keyDown(allButton, { key: 'ArrowRight' });

    expect(mockOnChange).toHaveBeenCalledWith('COOP_ADVENTURE');
  });

  it('navigates to previous category with arrow left', () => {
    render(
      <CategoryFilter
        selected="CORE_STRATEGY"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    const coreButton = screen.getByRole('button', {
      name: /Filter by Core Strategy/i,
    });
    fireEvent.keyDown(coreButton, { key: 'ArrowLeft' });

    expect(mockOnChange).toHaveBeenCalledWith('COOP_ADVENTURE');
  });

  it('renders uncategorized button', () => {
    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={mockCategoryCounts}
      />
    );

    expect(screen.getByText(/Uncategorized/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // uncategorized count
  });

  it('displays 0 count for categories with no games', () => {
    const countsWithZero = {
      ...mockCategoryCounts,
      PARTY_ICEBREAKERS: 0,
    };

    render(
      <CategoryFilter
        selected="all"
        onChange={mockOnChange}
        counts={countsWithZero}
      />
    );

    const buttons = screen.getAllByText('0');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
