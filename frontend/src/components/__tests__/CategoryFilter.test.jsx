import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CategoryFilter from '../CategoryFilter';

describe('CategoryFilter', () => {
  const mockSetCategory = jest.fn();
  const mockCategoryCounts = {
    COOP_ADVENTURE: 10,
    GATEWAY_STRATEGY: 15,
    CORE_STRATEGY: 20,
    KIDS_FAMILIES: 12,
    PARTY_ICEBREAKERS: 8,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all category buttons', () => {
    render(
      <CategoryFilter
        category="all"
        setCategory={mockSetCategory}
        categoryCounts={mockCategoryCounts}
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
        category="all"
        setCategory={mockSetCategory}
        categoryCounts={mockCategoryCounts}
      />
    );

    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('calls setCategory when button is clicked', () => {
    render(
      <CategoryFilter
        category="all"
        setCategory={mockSetCategory}
        categoryCounts={mockCategoryCounts}
      />
    );

    const coopButton = screen.getByText(/Co-op & Adventure/i);
    fireEvent.click(coopButton);

    expect(mockSetCategory).toHaveBeenCalledWith('COOP_ADVENTURE');
  });

  it('highlights active category', () => {
    const { container } = render(
      <CategoryFilter
        category="GATEWAY_STRATEGY"
        setCategory={mockSetCategory}
        categoryCounts={mockCategoryCounts}
      />
    );

    const buttons = container.querySelectorAll('button');
    const activeButton = Array.from(buttons).find(btn =>
      btn.textContent.includes('Gateway Strategy')
    );

    // Active button should have different styling (check for specific class or attribute)
    expect(activeButton).toHaveClass(/active|selected|bg-amber/i);
  });
});
