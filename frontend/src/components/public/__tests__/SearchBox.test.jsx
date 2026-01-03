import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SearchBox from '../SearchBox';

describe('SearchBox', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('renders with default placeholder', () => {
    render(<SearchBox value="" onChange={mockOnChange} />);

    const searchBox = screen.getByPlaceholderText('Search games...');
    expect(searchBox).toBeInTheDocument();
  });

  it('renders with custom placeholder', () => {
    render(
      <SearchBox
        value=""
        onChange={mockOnChange}
        placeholder="Search by title..."
      />
    );

    const searchBox = screen.getByPlaceholderText('Search by title...');
    expect(searchBox).toBeInTheDocument();
  });

  it('displays the provided value', () => {
    render(<SearchBox value="Pandemic" onChange={mockOnChange} />);

    const searchBox = screen.getByRole('searchbox');
    expect(searchBox).toHaveValue('Pandemic');
  });

  it('calls onChange when user types (with debouncing)', async () => {
    let currentValue = '';
    const mockOnChangeWithUpdate = vi.fn((newValue) => {
      currentValue = newValue;
    });

    const { rerender } = render(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);

    const searchBox = screen.getByRole('searchbox');

    await act(async () => {
      fireEvent.change(searchBox, { target: { value: 'Catan' } });
    });

    // Should not be called immediately due to debouncing
    expect(mockOnChangeWithUpdate).not.toHaveBeenCalled();

    // Fast-forward time by 300ms (debounce delay) and flush React updates
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    // Now onChange should be called
    expect(mockOnChangeWithUpdate).toHaveBeenCalledTimes(1);
    expect(mockOnChangeWithUpdate).toHaveBeenCalledWith('Catan');

    // Simulate parent component updating the value prop
    currentValue = 'Catan'; // Update the current value
    rerender(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);
  });

  it('has correct aria-label matching placeholder', () => {
    const placeholder = 'Search games...';
    render(
      <SearchBox value="" onChange={mockOnChange} placeholder={placeholder} />
    );

    const searchBox = screen.getByRole('searchbox');
    expect(searchBox).toHaveAttribute('aria-label', placeholder);
  });

  it('has correct role attribute', () => {
    render(<SearchBox value="" onChange={mockOnChange} />);

    const searchBox = screen.getByRole('searchbox');
    expect(searchBox).toHaveAttribute('role', 'searchbox');
  });

  it('applies custom className when provided', () => {
    const customClass = 'custom-search-class';
    render(
      <SearchBox value="" onChange={mockOnChange} className={customClass} />
    );

    const searchBox = screen.getByRole('searchbox');
    expect(searchBox).toHaveClass(customClass);
  });

  it('calls onChange with empty string when cleared (with debouncing)', async () => {
    let currentValue = 'Some text';
    const mockOnChangeWithUpdate = vi.fn((newValue) => {
      currentValue = newValue;
    });

    const { rerender } = render(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);

    const searchBox = screen.getByRole('searchbox');

    await act(async () => {
      fireEvent.change(searchBox, { target: { value: '' } });
    });

    // Should not be called immediately due to debouncing
    expect(mockOnChangeWithUpdate).not.toHaveBeenCalled();

    // Fast-forward time by 300ms (debounce delay) and flush React updates
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    // Now onChange should be called
    expect(mockOnChangeWithUpdate).toHaveBeenCalledTimes(1);
    expect(mockOnChangeWithUpdate).toHaveBeenCalledWith('');

    // Simulate parent component updating the value prop
    currentValue = ''; // Update the current value
    rerender(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);
  });

  it('debounces multiple rapid changes', async () => {
    let currentValue = '';
    const mockOnChangeWithUpdate = vi.fn((newValue) => {
      currentValue = newValue;
    });

    const { rerender } = render(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);

    const searchBox = screen.getByRole('searchbox');

    // Type multiple characters rapidly - wrap in act to handle state updates
    await act(async () => {
      fireEvent.change(searchBox, { target: { value: 'C' } });
      vi.advanceTimersByTime(100);
      fireEvent.change(searchBox, { target: { value: 'Ca' } });
      vi.advanceTimersByTime(100);
      fireEvent.change(searchBox, { target: { value: 'Cat' } });
      vi.advanceTimersByTime(100);
      fireEvent.change(searchBox, { target: { value: 'Cata' } });
      vi.advanceTimersByTime(100);
      fireEvent.change(searchBox, { target: { value: 'Catan' } });
    });

    // Should not be called yet
    expect(mockOnChangeWithUpdate).not.toHaveBeenCalled();

    // Fast-forward past the debounce delay and flush React updates
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    // Should only be called once with the final value
    expect(mockOnChangeWithUpdate).toHaveBeenCalledTimes(1);
    expect(mockOnChangeWithUpdate).toHaveBeenCalledWith('Catan');

    // Simulate parent component updating the value prop
    currentValue = 'Catan'; // Update the current value
    rerender(<SearchBox value={currentValue} onChange={mockOnChangeWithUpdate} />);
  });
});
