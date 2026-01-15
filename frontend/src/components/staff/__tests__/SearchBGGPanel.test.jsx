/**
 * Tests for SearchBGGPanel component - BoardGameGeek search functionality
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import SearchBGGPanel from '../SearchBGGPanel';


// Mock GameImage component
vi.mock('../../GameImage', () => ({
  default: ({ url, alt, className }) => (
    <img src={url || '/placeholder.png'} alt={alt} className={className} data-testid="game-image" />
  ),
}));


describe('SearchBGGPanel', () => {
  let defaultProps;

  beforeEach(() => {
    defaultProps = {
      searchQuery: '',
      setSearchQuery: vi.fn(),
      isSearching: false,
      results: [],
      onSearch: vi.fn(),
      onAddToLibrary: vi.fn(),
    };
  });

  describe('Rendering', () => {
    test('renders with correct heading', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      expect(screen.getByText('Search BoardGameGeek')).toBeInTheDocument();
    });

    test('renders search input with placeholder', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const input = screen.getByPlaceholderText('Search title…');
      expect(input).toBeInTheDocument();
    });

    test('renders Search button', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      expect(screen.getByRole('button', { name: /Search/i })).toBeInTheDocument();
    });

    test('displays provided search query in input', () => {
      render(<SearchBGGPanel {...defaultProps} searchQuery="Pandemic" />);
      expect(screen.getByDisplayValue('Pandemic')).toBeInTheDocument();
    });

    test('does not render results grid when results are empty', () => {
      render(<SearchBGGPanel {...defaultProps} results={[]} />);
      expect(screen.queryByTestId('game-image')).not.toBeInTheDocument();
    });

    test('does not render results grid when results are null', () => {
      render(<SearchBGGPanel {...defaultProps} results={null} />);
      expect(screen.queryByTestId('game-image')).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    test('calls setSearchQuery when input value changes', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const input = screen.getByPlaceholderText('Search title…');
      fireEvent.change(input, { target: { value: 'Catan' } });
      expect(defaultProps.setSearchQuery).toHaveBeenCalledWith('Catan');
    });

    test('calls onSearch when Search button clicked', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const searchButton = screen.getByRole('button', { name: /Search/i });
      fireEvent.click(searchButton);
      expect(defaultProps.onSearch).toHaveBeenCalledTimes(1);
    });

    test('calls onSearch when Enter key pressed in input', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const input = screen.getByPlaceholderText('Search title…');
      fireEvent.keyDown(input, { key: 'Enter' });
      expect(defaultProps.onSearch).toHaveBeenCalledTimes(1);
    });

    test('does not call onSearch on other key presses', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const input = screen.getByPlaceholderText('Search title…');
      fireEvent.keyDown(input, { key: 'Tab' });
      fireEvent.keyDown(input, { key: 'Escape' });
      fireEvent.keyDown(input, { key: 'a' });
      expect(defaultProps.onSearch).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    test('shows "Searching…" when isSearching is true', () => {
      render(<SearchBGGPanel {...defaultProps} isSearching={true} />);
      expect(screen.getByText('Searching…')).toBeInTheDocument();
    });

    test('shows "Search" when isSearching is false', () => {
      render(<SearchBGGPanel {...defaultProps} isSearching={false} />);
      expect(screen.getByText('Search')).toBeInTheDocument();
    });

    test('Search button is disabled when searching', () => {
      render(<SearchBGGPanel {...defaultProps} isSearching={true} />);
      const searchButton = screen.getByRole('button', { name: /Searching/i });
      expect(searchButton).toBeDisabled();
    });

    test('Search button is enabled when not searching', () => {
      render(<SearchBGGPanel {...defaultProps} isSearching={false} />);
      const searchButton = screen.getByRole('button', { name: /Search/i });
      expect(searchButton).not.toBeDisabled();
    });
  });

  describe('Results Display', () => {
    const mockResults = [
      {
        bgg_id: 12345,
        title: 'Pandemic',
        players_min: 2,
        players_max: 4,
        playing_time: 45,
        image_url: 'https://example.com/pandemic.jpg',
      },
      {
        bgg_id: 67890,
        title: 'Catan',
        players_min: 3,
        players_max: 4,
        playing_time: 90,
        cloudinary_url: 'https://cloudinary.com/catan.jpg',
      },
    ];

    test('renders game cards when results are provided', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      expect(screen.getByText('Pandemic')).toBeInTheDocument();
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    test('displays game images', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      const images = screen.getAllByTestId('game-image');
      expect(images).toHaveLength(2);
    });

    test('displays player count information', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      expect(screen.getByText(/2–4/)).toBeInTheDocument();
      expect(screen.getByText(/3–4/)).toBeInTheDocument();
    });

    test('displays playing time', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      expect(screen.getByText(/45 mins/)).toBeInTheDocument();
      expect(screen.getByText(/90 mins/)).toBeInTheDocument();
    });

    test('handles missing player count with question marks', () => {
      const incompleteResults = [
        {
          bgg_id: 11111,
          title: 'Mystery Game',
          players_min: null,
          players_max: null,
          playing_time: null,
        },
      ];
      render(<SearchBGGPanel {...defaultProps} results={incompleteResults} />);
      expect(screen.getByText('?–?')).toBeInTheDocument();
      expect(screen.getByText(/\? mins/)).toBeInTheDocument();
    });

    test('prefers cloudinary_url over image_url', () => {
      const gameWithBothUrls = [
        {
          bgg_id: 99999,
          title: 'Test Game',
          cloudinary_url: 'https://cloudinary.com/test.jpg',
          image_url: 'https://example.com/test.jpg',
        },
      ];
      render(<SearchBGGPanel {...defaultProps} results={gameWithBothUrls} />);
      const image = screen.getByTestId('game-image');
      expect(image).toHaveAttribute('src', 'https://cloudinary.com/test.jpg');
    });
  });

  describe('Category Buttons', () => {
    const mockResults = [
      {
        bgg_id: 12345,
        title: 'Pandemic',
        players_min: 2,
        players_max: 4,
        playing_time: 45,
      },
    ];

    test('renders category buttons for each category', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      expect(screen.getByText(/Add to Co-op & Adventure/i)).toBeInTheDocument();
      expect(screen.getByText(/Add to Core Strategy/i)).toBeInTheDocument();
      expect(screen.getByText(/Add to Gateway Strategy/i)).toBeInTheDocument();
      expect(screen.getByText(/Add to Kids & Families/i)).toBeInTheDocument();
      expect(screen.getByText(/Add to Party & Icebreakers/i)).toBeInTheDocument();
    });

    test('renders "Choose Category…" button', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      expect(screen.getByText('Choose Category…')).toBeInTheDocument();
    });

    test('calls onAddToLibrary with game and category when category button clicked', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      const addToCoopButton = screen.getByText(/Add to Co-op & Adventure/i);
      fireEvent.click(addToCoopButton);
      expect(defaultProps.onAddToLibrary).toHaveBeenCalledWith(
        mockResults[0],
        'COOP_ADVENTURE'
      );
    });

    test('calls onAddToLibrary with game and null when "Choose Category…" clicked', () => {
      render(<SearchBGGPanel {...defaultProps} results={mockResults} />);
      const chooseCategoryButton = screen.getByText('Choose Category…');
      fireEvent.click(chooseCategoryButton);
      expect(defaultProps.onAddToLibrary).toHaveBeenCalledWith(
        mockResults[0],
        null
      );
    });

    test('each game has its own set of category buttons', () => {
      const multipleResults = [
        { bgg_id: 111, title: 'Game One', players_min: 2, players_max: 4, playing_time: 30 },
        { bgg_id: 222, title: 'Game Two', players_min: 1, players_max: 6, playing_time: 60 },
      ];
      render(<SearchBGGPanel {...defaultProps} results={multipleResults} />);

      // Each game should have 6 buttons (5 categories + Choose Category)
      const allButtons = screen.getAllByRole('button');
      // 1 search button + 12 category buttons (6 per game)
      expect(allButtons).toHaveLength(13);
    });
  });

  describe('Edge Cases', () => {
    test('handles empty search query', () => {
      render(<SearchBGGPanel {...defaultProps} searchQuery="" />);
      const input = screen.getByPlaceholderText('Search title…');
      expect(input).toHaveValue('');
    });

    test('handles whitespace-only search query', () => {
      render(<SearchBGGPanel {...defaultProps} searchQuery="   " />);
      const input = screen.getByDisplayValue('   ');
      expect(input).toBeInTheDocument();
    });

    test('handles special characters in search query', () => {
      render(<SearchBGGPanel {...defaultProps} searchQuery="Ticket to Ride: Europe" />);
      expect(screen.getByDisplayValue('Ticket to Ride: Europe')).toBeInTheDocument();
    });

    test('handles game titles with special characters in results', () => {
      const specialCharResults = [
        {
          bgg_id: 33333,
          title: "Ticket to Ride: Europe – 15th Anniversary",
          players_min: 2,
          players_max: 5,
          playing_time: 60,
        },
      ];
      render(<SearchBGGPanel {...defaultProps} results={specialCharResults} />);
      expect(screen.getByText("Ticket to Ride: Europe – 15th Anniversary")).toBeInTheDocument();
    });

    test('handles very long game titles', () => {
      const longTitleResults = [
        {
          bgg_id: 44444,
          title: 'The Very Long Title Of An Absurdly Named Board Game That Goes On And On',
          players_min: 2,
          players_max: 6,
          playing_time: 120,
        },
      ];
      render(<SearchBGGPanel {...defaultProps} results={longTitleResults} />);
      expect(
        screen.getByText('The Very Long Title Of An Absurdly Named Board Game That Goes On And On')
      ).toBeInTheDocument();
    });

    test('handles large number of results', () => {
      const manyResults = Array.from({ length: 50 }, (_, i) => ({
        bgg_id: 10000 + i,
        title: `Game ${i + 1}`,
        players_min: 2,
        players_max: 4,
        playing_time: 30,
      }));
      render(<SearchBGGPanel {...defaultProps} results={manyResults} />);
      expect(screen.getByText('Game 1')).toBeInTheDocument();
      expect(screen.getByText('Game 50')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    test('search button has purple styling', () => {
      render(<SearchBGGPanel {...defaultProps} />);
      const searchButton = screen.getByRole('button', { name: /Search/i });
      expect(searchButton).toHaveClass('bg-purple-600');
    });

    test('panel has white background and rounded corners', () => {
      const { container } = render(<SearchBGGPanel {...defaultProps} />);
      const section = container.querySelector('section');
      expect(section).toHaveClass('bg-white', 'rounded-2xl');
    });
  });
});
