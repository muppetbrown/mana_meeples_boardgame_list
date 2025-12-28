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

  it('calls onPage when clicking previous button', () => {
    render(
      <Pagination page={3} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const prevButton = screen.getByRole('button', { name: /previous page/i });
    fireEvent.click(prevButton);

    expect(mockOnPage).toHaveBeenCalledWith(2);
  });

  it('calls onPage when clicking next button', () => {
    render(
      <Pagination page={2} pageSize={20} total={100} onPage={mockOnPage} />
    );

    const nextButton = screen.getByRole('button', { name: /next page/i });
    fireEvent.click(nextButton);

    expect(mockOnPage).toHaveBeenCalledWith(3);
  });

  it('shows first page button when page > 3', () => {
    render(
      <Pagination page={5} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const firstPageButton = screen.getByRole('button', {
      name: /go to first page/i,
    });
    expect(firstPageButton).toBeInTheDocument();
    expect(firstPageButton).toHaveTextContent('1');
  });

  it('calls onPage when clicking first page button', () => {
    render(
      <Pagination page={5} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const firstPageButton = screen.getByRole('button', {
      name: /go to first page/i,
    });
    fireEvent.click(firstPageButton);

    expect(mockOnPage).toHaveBeenCalledWith(1);
  });

  it('calls onPage when clicking last page button', () => {
    render(
      <Pagination page={1} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const lastPageButton = screen.getByRole('button', {
      name: /go to last page/i,
    });
    fireEvent.click(lastPageButton);

    expect(mockOnPage).toHaveBeenCalledWith(10);
  });

  it('hides results count when showResultsCount is false', () => {
    render(
      <Pagination
        page={1}
        pageSize={20}
        total={100}
        onPage={mockOnPage}
        showResultsCount={false}
      />
    );

    expect(screen.queryByText('1-20')).not.toBeInTheDocument();
  });

  it('shows results count by default', () => {
    render(
      <Pagination page={1} pageSize={20} total={100} onPage={mockOnPage} />
    );

    expect(screen.getByText('1-20')).toBeInTheDocument();
  });

  it('handles single page correctly', () => {
    render(
      <Pagination page={1} pageSize={20} total={15} onPage={mockOnPage} />
    );

    const prevButton = screen.getByRole('button', { name: /previous page/i });
    const nextButton = screen.getByRole('button', { name: /next page/i });

    expect(prevButton).toBeDisabled();
    expect(nextButton).toBeDisabled();
  });

  it('calculates correct end range for last page', () => {
    render(
      <Pagination page={5} pageSize={20} total={95} onPage={mockOnPage} />
    );

    expect(screen.getByText('81-95')).toBeInTheDocument();
  });

  it('has proper ARIA label on navigation', () => {
    render(
      <Pagination page={1} pageSize={20} total={100} onPage={mockOnPage} />
    );

    expect(screen.getByLabelText('Game results pagination')).toBeInTheDocument();
  });

  it('shows ellipsis before last page button', () => {
    const { container } = render(
      <Pagination page={1} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const ellipses = container.querySelectorAll('[aria-hidden="true"]');
    const ellipsisText = Array.from(ellipses).find(el => el.textContent === '...');
    expect(ellipsisText).toBeInTheDocument();
  });

  it('shows ellipsis after first page button', () => {
    const { container } = render(
      <Pagination page={5} pageSize={20} total={200} onPage={mockOnPage} />
    );

    const ellipses = container.querySelectorAll('[aria-hidden="true"]');
    expect(ellipses.length).toBeGreaterThan(0);
  });

  it('does not show first page button on early pages', () => {
    render(
      <Pagination page={2} pageSize={20} total={200} onPage={mockOnPage} />
    );

    expect(
      screen.queryByRole('button', { name: /go to first page/i })
    ).not.toBeInTheDocument();
  });

  it('does not show last page button when close to end', () => {
    render(
      <Pagination page={9} pageSize={20} total={200} onPage={mockOnPage} />
    );

    expect(
      screen.queryByRole('button', { name: /go to last page/i })
    ).not.toBeInTheDocument();
  });
});
