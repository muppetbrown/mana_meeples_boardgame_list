// TypeScript interfaces for game data
export interface Game {
  id: number;
  title: string;
  categories?: string;
  year?: number | null;
  players_min?: number | null;
  players_max?: number | null;
  min_players?: number | null;
  max_players?: number | null;
  playtime_min?: number | null;
  playtime_max?: number | null;
  playing_time?: number | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  image?: string | null;
  created_at?: string;
  bgg_id?: number | null;
  thumbnail_file?: string | null;
  mana_meeple_category?: string | null;
  description?: string | null;
  designers?: string[] | null;
  publishers?: string[] | null;
  mechanics?: string[] | null;
  artists?: string[] | null;
  average_rating?: number | null;
  complexity?: number | null;
  bgg_rank?: number | null;
  users_rated?: number | null;
  min_age?: number | null;
  is_cooperative?: boolean | null;
  nz_designer?: boolean | null;
  game_type?: string | null;
}

// API Response types
export interface PaginatedGamesResponse {
  total: number;
  page: number;
  page_size: number;
  items: Game[];
}

export interface CategoryCounts {
  all: number;
  uncategorized: number;
  [key: string]: number;
}

// Game filter parameters
export interface GameFilters {
  q?: string; // search query
  category?: string;
  designer?: string;
  nz_designer?: boolean;
  page?: number;
  page_size?: number;
  sort?: 'title_asc' | 'title_desc' | 'year_asc' | 'year_desc' | 'rating_asc' | 'rating_desc' | 'time_asc' | 'time_desc';
}

// Admin game operations
export interface GameCreateRequest {
  title: string;
  categories?: string;
  year?: number;
  players_min?: number;
  players_max?: number;
  playtime_min?: number;
  playtime_max?: number;
  thumbnail_url?: string;
  image?: string;
  bgg_id?: number;
  mana_meeple_category?: string;
  description?: string;
  designers?: string[];
  publishers?: string[];
  mechanics?: string[];
  artists?: string[];
  average_rating?: number;
  complexity?: number;
  bgg_rank?: number;
  users_rated?: number;
  min_age?: number;
  is_cooperative?: boolean;
  nz_designer?: boolean;
}

export interface GameUpdateRequest extends Partial<GameCreateRequest> {
  id?: number;
}

// BGG Integration types
export interface BGGImportRequest {
  bgg_id: number;
  force?: boolean;
}

export interface BulkOperationRequest {
  csv_data: string;
}

// UI Component types
export interface GameCardProps {
  game: Game;
  lazy?: boolean;
  onShare?: (game: Game) => void;
}

// Recently viewed functionality
export interface RecentlyViewedGame extends Game {
  viewedAt: string;
}