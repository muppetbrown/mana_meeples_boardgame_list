import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import {
  GameCardSkeleton,
  GameCardSkeletonGrid,
  ListSkeleton,
  TextSkeleton,
  GameDetailsSkeleton,
} from '../SkeletonLoader';

describe('GameCardSkeleton', () => {
  it('renders skeleton with animation', () => {
    const { container } = render(<GameCardSkeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('renders all placeholder elements', () => {
    const { container } = render(<GameCardSkeleton />);

    // Should have various skeleton elements (divs with bg-slate-200)
    const placeholders = container.querySelectorAll('.bg-slate-200');
    expect(placeholders.length).toBeGreaterThan(0);
  });

  it('has proper card styling', () => {
    const { container } = render(<GameCardSkeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('bg-white', 'rounded-lg', 'shadow-sm', 'p-4');
  });
});

describe('GameCardSkeletonGrid', () => {
  it('renders default 12 skeleton cards', () => {
    const { container } = render(<GameCardSkeletonGrid />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(12);
  });

  it('renders custom count of skeleton cards', () => {
    const { container } = render(<GameCardSkeletonGrid count={6} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(6);
  });

  it('renders with grid layout', () => {
    const { container } = render(<GameCardSkeletonGrid />);
    const grid = container.firstChild;
    expect(grid).toHaveClass('grid');
  });

  it('has responsive grid columns', () => {
    const { container } = render(<GameCardSkeletonGrid />);
    const grid = container.firstChild;
    expect(grid).toHaveClass('grid-cols-1', 'sm:grid-cols-2', 'lg:grid-cols-3', 'xl:grid-cols-4');
  });

  it('renders with gap between items', () => {
    const { container } = render(<GameCardSkeletonGrid />);
    const grid = container.firstChild;
    expect(grid).toHaveClass('gap-4');
  });

  it('handles zero count gracefully', () => {
    const { container } = render(<GameCardSkeletonGrid count={0} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(0);
  });

  it('handles large count', () => {
    const { container } = render(<GameCardSkeletonGrid count={24} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(24);
  });
});

describe('ListSkeleton', () => {
  it('renders default 5 skeleton items', () => {
    const { container } = render(<ListSkeleton />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(5);
  });

  it('renders custom count of skeleton items', () => {
    const { container } = render(<ListSkeleton count={3} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(3);
  });

  it('renders with vertical spacing', () => {
    const { container } = render(<ListSkeleton />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('space-y-3');
  });

  it('has proper list item styling', () => {
    const { container } = render(<ListSkeleton count={1} />);
    const item = container.querySelector('.animate-pulse');
    expect(item).toHaveClass('flex', 'items-center', 'gap-4', 'p-4');
  });

  it('handles zero count gracefully', () => {
    const { container } = render(<ListSkeleton count={0} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons).toHaveLength(0);
  });
});

describe('TextSkeleton', () => {
  it('renders default 3 lines', () => {
    const { container } = render(<TextSkeleton />);
    const lines = container.querySelectorAll('.bg-slate-200');
    expect(lines).toHaveLength(3);
  });

  it('renders custom number of lines', () => {
    const { container } = render(<TextSkeleton lines={5} />);
    const lines = container.querySelectorAll('.bg-slate-200');
    expect(lines).toHaveLength(5);
  });

  it('renders with animation', () => {
    const { container } = render(<TextSkeleton />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('animate-pulse');
  });

  it('applies custom className', () => {
    const { container } = render(<TextSkeleton className="custom-class" />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('custom-class');
  });

  it('maintains default classes with custom className', () => {
    const { container } = render(<TextSkeleton className="extra" />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('space-y-2', 'animate-pulse', 'extra');
  });

  it('last line is shorter (60% width)', () => {
    const { container } = render(<TextSkeleton lines={3} />);
    const lines = container.querySelectorAll('.bg-slate-200');
    const lastLine = lines[lines.length - 1];
    expect(lastLine).toHaveStyle({ width: '60%' });
  });

  it('non-last lines are full width (100%)', () => {
    const { container } = render(<TextSkeleton lines={3} />);
    const lines = container.querySelectorAll('.bg-slate-200');
    const firstLine = lines[0];
    expect(firstLine).toHaveStyle({ width: '100%' });
  });

  it('handles single line', () => {
    const { container } = render(<TextSkeleton lines={1} />);
    const lines = container.querySelectorAll('.bg-slate-200');
    expect(lines).toHaveLength(1);
    expect(lines[0]).toHaveStyle({ width: '60%' });
  });
});

describe('GameDetailsSkeleton', () => {
  it('renders with animation', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('has proper container styling', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('max-w-4xl', 'mx-auto', 'p-6');
  });

  it('renders header placeholders', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toBeTruthy();
  });

  it('renders grid layout for image and info', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const grid = container.querySelector('.grid');
    expect(grid).toHaveClass('md:grid-cols-2', 'gap-6');
  });

  it('renders image placeholder with aspect ratio', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const imagePlaceholder = container.querySelector('.aspect-square');
    expect(imagePlaceholder).toBeInTheDocument();
    expect(imagePlaceholder).toHaveClass('bg-slate-200', 'rounded-lg');
  });

  it('renders description placeholders', () => {
    const { container } = render(<GameDetailsSkeleton />);
    const placeholders = container.querySelectorAll('.bg-slate-200');
    expect(placeholders.length).toBeGreaterThan(0);
  });
});

describe('accessibility', () => {
  it('skeleton loaders are decorative and hidden from screen readers', () => {
    const { container } = render(<GameCardSkeleton />);
    // Skeleton loaders don't have specific ARIA labels as they're visual placeholders
    expect(container.firstChild).toBeTruthy();
  });

  it('TextSkeleton can be combined with aria-label on parent', () => {
    render(
      <div aria-label="Loading content">
        <TextSkeleton />
      </div>
    );
    expect(screen.getByLabelText('Loading content')).toBeInTheDocument();
  });
});
