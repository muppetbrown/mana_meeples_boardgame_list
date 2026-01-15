/**
 * Tests for BulkPanels components - BulkImportPanel, BulkCategorizePanel, BulkAfterGamePanel
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { BulkImportPanel, BulkCategorizePanel, BulkAfterGamePanel } from '../BulkPanels';


describe('BulkImportPanel', () => {
  let mockOnChange;
  let mockOnSubmit;

  beforeEach(() => {
    mockOnChange = vi.fn();
    mockOnSubmit = vi.fn();
  });

  describe('Rendering', () => {
    test('renders with correct heading', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('Bulk Import (CSV)')).toBeInTheDocument();
    });

    test('renders help text with CSV format example', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText(/Paste rows/)).toBeInTheDocument();
      expect(screen.getByText('bgg_id,title')).toBeInTheDocument();
    });

    test('renders textarea element', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    test('renders Import button', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('button', { name: /Import/i })).toBeInTheDocument();
    });

    test('displays provided value in textarea', () => {
      const csvData = '12345,Pandemic\n67890,Catan';
      render(<BulkImportPanel value={csvData} onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toHaveValue(csvData);
    });
  });

  describe('Interactions', () => {
    test('calls onChange when textarea content changes', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: '12345,Pandemic' } });
      expect(mockOnChange).toHaveBeenCalledWith('12345,Pandemic');
    });

    test('calls onSubmit when Import button clicked', () => {
      render(<BulkImportPanel value="12345,Pandemic" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    test('allows submitting with empty textarea', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    test('handles multi-line CSV input', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      const multiLineCSV = '12345,Pandemic\n67890,Catan\n11111,Gloomhaven';
      fireEvent.change(textarea, { target: { value: multiLineCSV } });
      expect(mockOnChange).toHaveBeenCalledWith(multiLineCSV);
    });
  });

  describe('Styling', () => {
    test('Import button has green styling', () => {
      render(<BulkImportPanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const importButton = screen.getByRole('button', { name: /Import/i });
      expect(importButton).toHaveClass('bg-green-600');
    });
  });
});


describe('BulkCategorizePanel', () => {
  let mockOnChange;
  let mockOnSubmit;

  beforeEach(() => {
    mockOnChange = vi.fn();
    mockOnSubmit = vi.fn();
  });

  describe('Rendering', () => {
    test('renders with correct heading', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('Bulk Categorize Existing (CSV)')).toBeInTheDocument();
    });

    test('renders help text with CSV format', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('bgg_id,category[,title]')).toBeInTheDocument();
    });

    test('shows category key example', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('CORE_STRATEGY')).toBeInTheDocument();
    });

    test('shows category label example', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('Core Strategy & Epics')).toBeInTheDocument();
    });

    test('renders textarea element', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    test('renders Categorize button', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('button', { name: /Categorize/i })).toBeInTheDocument();
    });

    test('displays provided value in textarea', () => {
      const csvData = '12345,CORE_STRATEGY,Gloomhaven';
      render(<BulkCategorizePanel value={csvData} onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toHaveValue(csvData);
    });
  });

  describe('Interactions', () => {
    test('calls onChange when textarea content changes', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: '12345,GATEWAY_STRATEGY' } });
      expect(mockOnChange).toHaveBeenCalledWith('12345,GATEWAY_STRATEGY');
    });

    test('calls onSubmit when Categorize button clicked', () => {
      render(<BulkCategorizePanel value="12345,CORE_STRATEGY" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const categorizeButton = screen.getByRole('button', { name: /Categorize/i });
      fireEvent.click(categorizeButton);
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    test('handles category key format in input', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: '12345,PARTY_ICEBREAKERS,Codenames' } });
      expect(mockOnChange).toHaveBeenCalledWith('12345,PARTY_ICEBREAKERS,Codenames');
    });

    test('handles category label format in input', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: '12345,Kids & Families,Ticket to Ride' } });
      expect(mockOnChange).toHaveBeenCalledWith('12345,Kids & Families,Ticket to Ride');
    });
  });

  describe('Styling', () => {
    test('Categorize button has blue styling', () => {
      render(<BulkCategorizePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const categorizeButton = screen.getByRole('button', { name: /Categorize/i });
      expect(categorizeButton).toHaveClass('bg-blue-600');
    });
  });
});


describe('BulkAfterGamePanel', () => {
  let mockOnChange;
  let mockOnSubmit;

  beforeEach(() => {
    mockOnChange = vi.fn();
    mockOnSubmit = vi.fn();
  });

  describe('Rendering', () => {
    test('renders with correct heading including emoji', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText(/Bulk Update AfterGame IDs/)).toBeInTheDocument();
    });

    test('renders help text with CSV format', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('bgg_id,aftergame_game_id[,title]')).toBeInTheDocument();
    });

    test('shows UUID example format', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText('ac3a5f77-3e19-47af-a61a-d648d04b02e2')).toBeInTheDocument();
    });

    test('renders example CSV format box', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText(/Example CSV format/)).toBeInTheDocument();
    });

    test('shows Gloomhaven in example', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getAllByText(/Gloomhaven/).length).toBeGreaterThan(0);
    });

    test('shows Terraforming Mars in example', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByText(/Terraforming Mars/)).toBeInTheDocument();
    });

    test('renders textarea element', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    test('textarea has placeholder text', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('placeholder');
      expect(textarea.getAttribute('placeholder')).toContain('bgg_id,aftergame_game_id,title');
    });

    test('renders Update AfterGame IDs button', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('button', { name: /Update AfterGame IDs/i })).toBeInTheDocument();
    });

    test('displays provided value in textarea', () => {
      const csvData = '174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven';
      render(<BulkAfterGamePanel value={csvData} onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      expect(screen.getByRole('textbox')).toHaveValue(csvData);
    });
  });

  describe('Interactions', () => {
    test('calls onChange when textarea content changes', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      const testData = '174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Test Game';
      fireEvent.change(textarea, { target: { value: testData } });
      expect(mockOnChange).toHaveBeenCalledWith(testData);
    });

    test('calls onSubmit when Update button clicked', () => {
      render(<BulkAfterGamePanel value="174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const updateButton = screen.getByRole('button', { name: /Update AfterGame IDs/i });
      fireEvent.click(updateButton);
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    test('handles valid UUID format in input', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      const validUUID = '12345,550e8400-e29b-41d4-a716-446655440000,Test Game';
      fireEvent.change(textarea, { target: { value: validUUID } });
      expect(mockOnChange).toHaveBeenCalledWith(validUUID);
    });

    test('handles multi-line input with multiple games', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const textarea = screen.getByRole('textbox');
      const multiLineData =
        '174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven\n' +
        '167791,bd4b6e88-4c2a-48bf-b71b-e759e15c13f3,Terraforming Mars';
      fireEvent.change(textarea, { target: { value: multiLineData } });
      expect(mockOnChange).toHaveBeenCalledWith(multiLineData);
    });
  });

  describe('Styling', () => {
    test('Update button has emerald styling', () => {
      render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const updateButton = screen.getByRole('button', { name: /Update AfterGame IDs/i });
      expect(updateButton).toHaveClass('bg-emerald-600');
    });

    test('example box has emerald background styling', () => {
      const { container } = render(<BulkAfterGamePanel value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />);
      const exampleBox = container.querySelector('.bg-emerald-50');
      expect(exampleBox).toBeInTheDocument();
    });
  });
});


describe('BulkPanels Integration', () => {
  test('all panels can be rendered together', () => {
    const mockFn = vi.fn();
    render(
      <div>
        <BulkImportPanel value="" onChange={mockFn} onSubmit={mockFn} />
        <BulkCategorizePanel value="" onChange={mockFn} onSubmit={mockFn} />
        <BulkAfterGamePanel value="" onChange={mockFn} onSubmit={mockFn} />
      </div>
    );

    expect(screen.getByText('Bulk Import (CSV)')).toBeInTheDocument();
    expect(screen.getByText('Bulk Categorize Existing (CSV)')).toBeInTheDocument();
    expect(screen.getByText(/Bulk Update AfterGame IDs/)).toBeInTheDocument();
  });

  test('each panel has distinct button styling', () => {
    const mockFn = vi.fn();
    render(
      <div>
        <BulkImportPanel value="" onChange={mockFn} onSubmit={mockFn} />
        <BulkCategorizePanel value="" onChange={mockFn} onSubmit={mockFn} />
        <BulkAfterGamePanel value="" onChange={mockFn} onSubmit={mockFn} />
      </div>
    );

    const importBtn = screen.getByRole('button', { name: /^Import$/i });
    const categorizeBtn = screen.getByRole('button', { name: /Categorize/i });
    const updateBtn = screen.getByRole('button', { name: /Update AfterGame IDs/i });

    expect(importBtn).toHaveClass('bg-green-600');
    expect(categorizeBtn).toHaveClass('bg-blue-600');
    expect(updateBtn).toHaveClass('bg-emerald-600');
  });
});
