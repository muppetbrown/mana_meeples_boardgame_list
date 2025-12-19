import React from 'react';
import { vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from '../Pagination';

describe('Pagination', () => {
  const mockOnPage = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays correct results count', () => {
    render(
      <Pagination page={1} pageSize={20} total={100} onPage={mockOnPage} />
    );

    expect(screen.getByText('1-20')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('disables previous button on first page', () => {
    render(
      <Pagination page={1} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const prevButton = screen.getByRole('button', { name: /previous page/i });
    expect(prevButton).toBeDisabled();
  });

  it('disables next button on last page', () => {
    render(
      <Pagination page={5} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const nextButton = screen.getByRole('button', { name: /next page/i });
    expect(nextButton).toBeDisabled();
  });

  it('calls onPage when clicking page number', () => {
    render(
      <Pagination page={2} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const pageButton = screen.getByRole('button', { name: /go to page 3/i });
    fireEvent.click(pageButton);

    expect(mockOnPage).toHaveBeenCalledTimes(1);
    expect(mockOnPage).toHaveBeenCalledWith(3);
  });

  it('highlights current page', () => {
    render(
      <Pagination page={3} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const currentPageButton = screen.getByRole('button', {
      name: /current page 3/i,
    });
    expect(currentPageButton).toHaveClass('bg-emerald-500', 'text-white');
    expect(currentPageButton).toHaveAttribute('aria-current', 'page');
  });

  it('shows jump to last page button when far from end', () => {
    render(
      <Pagination page={1} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const lastPageButton = screen.getByRole('button', {
      name: /go to last page/i,
    });
    expect(lastPageButton).toBeInTheDocument();
    expect(lastPageButton).toHaveTextContent('10');
  });
});
