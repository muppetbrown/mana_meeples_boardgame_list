import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SearchBox from '../SearchBox';

describe('SearchBox', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
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

  it('calls onChange when user types', () => {
    render(<SearchBox value="" onChange={mockOnChange} />);

    const searchBox = screen.getByRole('searchbox');
    fireEvent.change(searchBox, { target: { value: 'Catan' } });

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith('Catan');
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

  it('calls onChange with empty string when cleared', () => {
    render(<SearchBox value="Some text" onChange={mockOnChange} />);

    const searchBox = screen.getByRole('searchbox');
    fireEvent.change(searchBox, { target: { value: '' } });

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith('');
  });
});
