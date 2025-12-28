import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SortSelect from '../SortSelect';

describe('SortSelect', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  describe('basic rendering', () => {
    it('renders sort dropdown with default sort', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toBeInTheDocument();
      expect(select).toHaveValue('title');
    });

    it('renders direction toggle button', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toBeInTheDocument();
    });

    it('displays all sort options', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      expect(screen.getByRole('option', { name: 'Title' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Year' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Rating' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Time' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Added' })).toBeInTheDocument();
    });

    it('applies custom className to wrapper', () => {
      const { container } = render(
        <SortSelect sort="title_asc" onChange={mockOnChange} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('applies custom id to select element', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} id="custom-id" />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveAttribute('id', 'custom-id');
    });
  });

  describe('current sort state display', () => {
    it('displays correct field for title_asc', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('title');
    });

    it('displays correct field for year_desc', () => {
      render(<SortSelect sort="year_desc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('year');
    });

    it('displays correct field for rating_desc', () => {
      render(<SortSelect sort="rating_desc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('rating');
    });

    it('displays correct field for time_asc', () => {
      render(<SortSelect sort="time_asc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('time');
    });

    it('displays correct field for date_added_desc', () => {
      render(<SortSelect sort="date_added_desc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('date_added');
    });

    it('shows ascending icon for ascending sort', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toHaveTextContent('↑');
    });

    it('shows descending icon for descending sort', () => {
      render(<SortSelect sort="year_desc" onChange={mockOnChange} />);
      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toHaveTextContent('↓');
    });
  });

  describe('changing sort field', () => {
    it('calls onChange with year_desc when year is selected', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      fireEvent.change(select, { target: { value: 'year' } });

      expect(mockOnChange).toHaveBeenCalledWith('year_desc');
    });

    it('calls onChange with rating_desc when rating is selected', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      fireEvent.change(select, { target: { value: 'rating' } });

      expect(mockOnChange).toHaveBeenCalledWith('rating_desc');
    });

    it('calls onChange with time_asc when time is selected', () => {
      render(<SortSelect sort="year_desc" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      fireEvent.change(select, { target: { value: 'time' } });

      expect(mockOnChange).toHaveBeenCalledWith('time_asc');
    });

    it('uses default direction for each field', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });

      // Title defaults to asc
      fireEvent.change(select, { target: { value: 'title' } });
      expect(mockOnChange).toHaveBeenLastCalledWith('title_asc');

      // Year defaults to desc
      fireEvent.change(select, { target: { value: 'year' } });
      expect(mockOnChange).toHaveBeenLastCalledWith('year_desc');

      // Rating defaults to desc
      fireEvent.change(select, { target: { value: 'rating' } });
      expect(mockOnChange).toHaveBeenLastCalledWith('rating_desc');
    });
  });

  describe('toggling sort direction', () => {
    it('toggles from asc to desc', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);

      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      fireEvent.click(button);

      expect(mockOnChange).toHaveBeenCalledWith('title_desc');
    });

    it('toggles from desc to asc', () => {
      render(<SortSelect sort="year_desc" onChange={mockOnChange} />);

      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      fireEvent.click(button);

      expect(mockOnChange).toHaveBeenCalledWith('year_asc');
    });

    it('maintains current sort field when toggling', () => {
      render(<SortSelect sort="rating_desc" onChange={mockOnChange} />);

      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      fireEvent.click(button);

      expect(mockOnChange).toHaveBeenCalledWith('rating_asc');
    });

    it('can toggle multiple times', () => {
      const { rerender } = render(<SortSelect sort="title_asc" onChange={mockOnChange} />);

      const button = screen.getByRole('button', { name: /toggle sort direction/i });

      fireEvent.click(button);
      expect(mockOnChange).toHaveBeenLastCalledWith('title_desc');

      rerender(<SortSelect sort="title_desc" onChange={mockOnChange} />);

      fireEvent.click(button);
      expect(mockOnChange).toHaveBeenLastCalledWith('title_asc');
    });
  });

  describe('invalid sort handling', () => {
    it('defaults to title when sort key is invalid', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      render(<SortSelect sort="invalid_sort_asc" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('title');
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unknown sort key in: invalid_sort_asc')
      );

      consoleWarnSpy.mockRestore();
    });

    it('handles malformed sort string gracefully', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      render(<SortSelect sort="xyz" onChange={mockOnChange} />);

      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveValue('title');

      consoleWarnSpy.mockRestore();
    });
  });

  describe('accessibility', () => {
    it('has screen reader only label', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      expect(screen.getByText('Choose how to sort games', { selector: '.sr-only' })).toBeInTheDocument();
    });

    it('has aria-label on select', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const select = screen.getByRole('combobox', { name: /choose sort field/i });
      expect(select).toHaveAttribute('aria-label', 'Choose sort field');
    });

    it('has descriptive aria-label on direction button', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const button = screen.getByRole('button', { name: /currently ascending/i });
      expect(button).toHaveAttribute('aria-label', expect.stringContaining('ascending'));
    });

    it('updates aria-label when direction changes', () => {
      const { rerender } = render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      expect(screen.getByRole('button', { name: /currently ascending/i })).toBeInTheDocument();

      rerender(<SortSelect sort="title_desc" onChange={mockOnChange} />);
      expect(screen.getByRole('button', { name: /currently descending/i })).toBeInTheDocument();
    });

    it('has live region for status updates', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    });

    it('announces current sort in live region', () => {
      render(<SortSelect sort="year_desc" onChange={mockOnChange} />);
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveTextContent('Currently sorting by year in descending order');
    });
  });

  describe('button tooltip', () => {
    it('has descriptive title on direction button', () => {
      render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      const button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toHaveAttribute('title', expect.stringContaining('ascending'));
    });

    it('updates title when direction changes', () => {
      const { rerender } = render(<SortSelect sort="title_asc" onChange={mockOnChange} />);
      let button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toHaveAttribute('title', expect.stringContaining('ascending'));

      rerender(<SortSelect sort="title_desc" onChange={mockOnChange} />);
      button = screen.getByRole('button', { name: /toggle sort direction/i });
      expect(button).toHaveAttribute('title', expect.stringContaining('descending'));
    });
  });

  describe('passing additional props', () => {
    it('passes additional props to select element', () => {
      render(
        <SortSelect
          sort="title_asc"
          onChange={mockOnChange}
          data-testid="custom-select"
          disabled={false}
        />
      );
      const select = screen.getByTestId('custom-select');
      expect(select).toBeInTheDocument();
    });
  });
});
