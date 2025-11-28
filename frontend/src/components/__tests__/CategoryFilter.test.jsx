import React from 'react';
import { render, screen } from '@testing-library/react';
import CategoryFilter from '../CategoryFilter';

describe('CategoryFilter', () => {
  const mockOnChange = jest.fn();
  const mockCategoryCounts = {
    all: 65,
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
});
