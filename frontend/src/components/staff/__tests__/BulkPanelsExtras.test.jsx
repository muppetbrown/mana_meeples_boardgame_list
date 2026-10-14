import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BulkImportPanel, BulkCategorizePanel, BulkAfterGamePanel } from '../BulkPanels';

const loadFile = async (container, text) => {
  const input = container.querySelector('input[type="file"]');
  const file = new File([text], 'games.csv', { type: 'text/csv' });
  // jsdom File lacks text() in some versions
  if (!file.text) file.text = async () => text;
  fireEvent.change(input, { target: { files: [file] } });
};

describe('Bulk panel extras', () => {
  test('"Load from file" puts the file contents in the textarea', async () => {
    const onChange = vi.fn();
    const { container } = render(<BulkImportPanel value="" onChange={onChange} onSubmit={() => {}} />);
    await loadFile(container, '1\n2\n');
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('1\n2\n'));
  });

  test('Clear empties the textarea; hidden while busy', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender } = render(<BulkImportPanel value="1" onChange={onChange} onSubmit={() => {}} />);
    await user.click(screen.getByText('Clear'));
    expect(onChange).toHaveBeenCalledWith('');
    rerender(<BulkImportPanel value="1" onChange={onChange} onSubmit={() => {}} busy />);
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
  });

  test('singular line count and submit callback', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<BulkImportPanel value="42" onChange={() => {}} onSubmit={onSubmit} />);
    await user.click(screen.getByRole('button', { name: 'Import (1 line)' }));
    expect(onSubmit).toHaveBeenCalled();
  });

  test('queued banner can be dismissed', async () => {
    const user = userEvent.setup();
    const onDismissQueued = vi.fn();
    render(
      <BulkImportPanel value="" onChange={() => {}} onSubmit={() => {}} queued={{ message: 'Started' }} onDismissQueued={onDismissQueued} />
    );
    await user.click(screen.getByLabelText('Dismiss'));
    expect(onDismissQueued).toHaveBeenCalled();
  });

  test('categorize panel shows inline results and supports dismiss', async () => {
    const user = userEvent.setup();
    const onDismissResult = vi.fn();
    render(
      <BulkCategorizePanel
        value="" onChange={() => {}} onSubmit={() => {}}
        result={{ updated: ['a'], not_found: [], errors: ['bad'] }}
        onDismissResult={onDismissResult}
      />
    );
    expect(screen.getByText('bad')).toBeInTheDocument();
    await user.click(screen.getByText('Dismiss'));
    expect(onDismissResult).toHaveBeenCalled();
  });

  test('AfterGame panel renders results and respects busy', () => {
    render(
      <BulkAfterGamePanel
        value="x" onChange={() => {}} onSubmit={() => {}} busy
        result={{ updated: ['ok'], not_found: [], errors: [] }}
      />
    );
    expect(screen.getByRole('button', { name: 'Working…' })).toBeDisabled();
    expect(screen.getByText('ok')).toBeInTheDocument();
  });
});
