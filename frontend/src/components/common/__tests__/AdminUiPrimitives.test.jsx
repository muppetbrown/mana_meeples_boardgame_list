import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Modal from '../Modal';
import ConfirmDialog from '../ConfirmDialog';
import Thumbnail from '../Thumbnail';
import BulkResultSummary, { buildBulkLog } from '../../staff/BulkResultSummary';

vi.mock('../../../api/client', () => ({ imageProxyUrl: (u) => `proxy:${u}` }));

describe('Modal', () => {
  test('exposes dialog semantics and moves focus inside', () => {
    render(
      <Modal onClose={() => {}} labelledBy="t">
        <h2 id="t">Title</h2>
        <button>First</button>
      </Modal>
    );
    const dialog = screen.getByRole('dialog', { name: 'Title' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('First')).toHaveFocus();
  });

  test('traps Tab focus inside the dialog', async () => {
    const user = userEvent.setup();
    render(
      <Modal onClose={() => {}} label="x">
        <button>A</button>
        <button>B</button>
      </Modal>
    );
    expect(screen.getByText('A')).toHaveFocus();
    await user.tab();
    expect(screen.getByText('B')).toHaveFocus();
    await user.tab();
    expect(screen.getByText('A')).toHaveFocus(); // wrapped
    await user.tab({ shift: true });
    expect(screen.getByText('B')).toHaveFocus(); // wrapped backwards
  });

  test('restores focus to the trigger on unmount', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();
    const { unmount } = render(<Modal onClose={() => {}} label="x"><button>A</button></Modal>);
    unmount();
    expect(trigger).toHaveFocus();
    trigger.remove();
  });

  test('only the topmost modal reacts to Escape', async () => {
    const user = userEvent.setup();
    const outer = vi.fn();
    const inner = vi.fn();
    render(
      <>
        <Modal onClose={outer} label="outer"><button>o</button></Modal>
        <Modal onClose={inner} label="inner"><button>i</button></Modal>
      </>
    );
    await user.keyboard('{Escape}');
    expect(inner).toHaveBeenCalledTimes(1);
    expect(outer).not.toHaveBeenCalled();
  });

  test('backdrop click closes but clicks inside do not', () => {
    const onClose = vi.fn();
    const { container } = render(<Modal onClose={onClose} label="x"><button>A</button></Modal>);
    fireEvent.mouseDown(screen.getByText('A'));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.mouseDown(container.firstChild);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe('ConfirmDialog', () => {
  test('confirm and cancel callbacks', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmDialog title="Sure?" message="Details" confirmLabel="Do it" onConfirm={onConfirm} onCancel={onCancel} />);
    expect(screen.getByText('Details')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Do it' }));
    expect(onConfirm).toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalled();
  });

  test('requireText gate is case-insensitive and enter-submittable', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ConfirmDialog title="T" requireText="reimport" confirmLabel="Go" onConfirm={onConfirm} onCancel={() => {}} />);
    await user.keyboard('{Enter}');
    expect(onConfirm).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText(/type reimport/i), 'REIMPORT{Enter}');
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});

describe('Thumbnail', () => {
  test('renders a proxied image and falls back on error', () => {
    render(<Thumbnail src="http://x/y.jpg" alt="Game" />);
    const img = screen.getByAltText('Game');
    expect(img).toHaveAttribute('src', 'proxy:http://x/y.jpg');
    fireEvent.error(img);
    expect(screen.getByText('No img')).toBeInTheDocument();
    expect(screen.queryByAltText('Game')).not.toBeInTheDocument();
  });

  test('shows the placeholder when there is no source', () => {
    render(<Thumbnail src={null} />);
    expect(screen.getByText('No img')).toBeInTheDocument();
  });
});

describe('BulkResultSummary', () => {
  const result = { updated: ['ok 1'], not_found: ['missing 1'], errors: ['bad line'] };

  test('shows counts and each category of result', () => {
    render(<BulkResultSummary result={result} />);
    expect(screen.getByText(/1 updated · 1 not found · 1 errors/)).toBeInTheDocument();
    expect(screen.getByText('bad line')).toBeInTheDocument();
    expect(screen.getByText('missing 1')).toBeInTheDocument();
  });

  test('renders nothing without a result and supports dismiss', async () => {
    const user = userEvent.setup();
    const { container, rerender } = render(<BulkResultSummary result={null} />);
    expect(container).toBeEmptyDOMElement();
    const onDismiss = vi.fn();
    rerender(<BulkResultSummary result={result} onDismiss={onDismiss} />);
    await user.click(screen.getByText('Dismiss'));
    expect(onDismiss).toHaveBeenCalled();
  });

  test('buildBulkLog lists all sections', () => {
    expect(buildBulkLog(result)).toBe('Updated:\nok 1\n\nNot found:\nmissing 1\n\nErrors:\nbad line\n');
  });
});

describe('Modal edge cases', () => {
  test('Tab is swallowed when the dialog has nothing focusable', async () => {
    const user = userEvent.setup();
    render(
      <Modal onClose={() => {}} label="empty">
        <p>No controls</p>
      </Modal>
    );
    // focus falls back to the dialog panel itself
    expect(screen.getByRole('dialog')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('dialog')).toHaveFocus();
  });

  test('keys other than Tab/Escape are ignored', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<Modal onClose={onClose} label="x"><button>A</button></Modal>);
    await user.keyboard('a');
    expect(onClose).not.toHaveBeenCalled();
  });

  test('closeOnBackdrop=false ignores backdrop clicks', () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal onClose={onClose} label="x" closeOnBackdrop={false}><button>A</button></Modal>
    );
    fireEvent.mouseDown(container.firstChild);
    expect(onClose).not.toHaveBeenCalled();
  });
});
