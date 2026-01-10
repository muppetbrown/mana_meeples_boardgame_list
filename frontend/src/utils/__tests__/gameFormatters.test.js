/**
 * Tests for gameFormatters utility
 */
import { describe, it, expect } from 'vitest';
import {
  formatRating,
  formatComplexity,
  formatTime,
  formatPlayerCount
} from '../gameFormatters';

describe('gameFormatters', () => {
  describe('formatRating()', () => {
    it('formats valid rating with 1 decimal place', () => {
      expect(formatRating(7.5)).toBe('7.5');
      expect(formatRating(8.123)).toBe('8.1');
      expect(formatRating(9.999)).toBe('10.0');
    });

    it('formats integer ratings with .0', () => {
      expect(formatRating(7)).toBe('7.0');
      expect(formatRating(10)).toBe('10.0');
    });

    it('returns null for zero rating', () => {
      expect(formatRating(0)).toBeNull();
    });

    it('returns null for null rating', () => {
      expect(formatRating(null)).toBeNull();
    });

    it('returns null for undefined rating', () => {
      expect(formatRating(undefined)).toBeNull();
    });

    it('handles edge case: very small positive number', () => {
      expect(formatRating(0.1)).toBe('0.1');
    });

    it('handles edge case: maximum rating', () => {
      expect(formatRating(10)).toBe('10.0');
    });
  });

  describe('formatComplexity()', () => {
    it('formats valid complexity with 1 decimal place', () => {
      expect(formatComplexity(2.5)).toBe('2.5');
      expect(formatComplexity(3.123)).toBe('3.1');
      expect(formatComplexity(4.999)).toBe('5.0');
    });

    it('formats integer complexity with .0', () => {
      expect(formatComplexity(1)).toBe('1.0');
      expect(formatComplexity(5)).toBe('5.0');
    });

    it('returns null for zero complexity', () => {
      expect(formatComplexity(0)).toBeNull();
    });

    it('returns null for null complexity', () => {
      expect(formatComplexity(null)).toBeNull();
    });

    it('returns null for undefined complexity', () => {
      expect(formatComplexity(undefined)).toBeNull();
    });

    it('handles edge case: minimum complexity', () => {
      expect(formatComplexity(1.0)).toBe('1.0');
    });

    it('handles edge case: maximum complexity', () => {
      expect(formatComplexity(5.0)).toBe('5.0');
    });
  });

  describe('formatTime()', () => {
    it('formats time range when min and max differ', () => {
      expect(formatTime(30, 60)).toBe('30-60 min');
      expect(formatTime(45, 90)).toBe('45-90 min');
    });

    it('formats single value when min and max are equal', () => {
      expect(formatTime(30, 30)).toBe('30 min');
      expect(formatTime(60, 60)).toBe('60 min');
    });

    it('formats single value when only min is provided', () => {
      expect(formatTime(45, null)).toBe('45 min');
      expect(formatTime(30, undefined)).toBe('30 min');
    });

    it('formats single value when only max is provided', () => {
      expect(formatTime(null, 60)).toBe('60 min');
      expect(formatTime(undefined, 90)).toBe('90 min');
    });

    it('returns default message when both are null', () => {
      expect(formatTime(null, null)).toBe('Time varies');
    });

    it('returns default message when both are undefined', () => {
      expect(formatTime(undefined, undefined)).toBe('Time varies');
    });

    it('returns default message when both are zero', () => {
      expect(formatTime(0, 0)).toBe('Time varies');
    });

    it('handles edge case: min is 0, max is valid', () => {
      expect(formatTime(0, 60)).toBe('60 min');
    });

    it('handles edge case: min is valid, max is 0', () => {
      expect(formatTime(30, 0)).toBe('30 min');
    });

    it('handles large time values', () => {
      expect(formatTime(120, 240)).toBe('120-240 min');
    });
  });

  describe('formatPlayerCount()', () => {
    it('returns null when game is undefined', () => {
      expect(formatPlayerCount(undefined)).toBeNull();
    });

    it('returns null when game is null', () => {
      expect(formatPlayerCount(null)).toBeNull();
    });

    it('formats player range when min and max differ', () => {
      const game = { players_min: 2, players_max: 4 };
      expect(formatPlayerCount(game)).toBe('2-4');
    });

    it('formats single player count when min equals max', () => {
      const game = { players_min: 4, players_max: 4 };
      expect(formatPlayerCount(game)).toBe('4');
    });

    it('returns null when min is missing', () => {
      const game = { players_max: 4 };
      expect(formatPlayerCount(game)).toBeNull();
    });

    it('returns null when max is missing', () => {
      const game = { players_min: 2 };
      expect(formatPlayerCount(game)).toBeNull();
    });

    it('returns null when both are missing', () => {
      const game = {};
      expect(formatPlayerCount(game)).toBeNull();
    });

    it('formats expanded range with asterisk when expansion extends max', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_min_with_expansions: 2,
        players_max_with_expansions: 6,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('2-6*');
    });

    it('formats expanded single value with asterisk', () => {
      const game = {
        players_min: 4,
        players_max: 4,
        players_min_with_expansions: 4,
        players_max_with_expansions: 6,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('4-6*');
    });

    it('uses expMin when provided for expansion range', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_min_with_expansions: 1,
        players_max_with_expansions: 6,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('1-6*');
    });

    it('falls back to baseMin when expMin is missing', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_max_with_expansions: 6,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('2-6*');
    });

    it('does not show asterisk when has_player_expansion is false', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_min_with_expansions: 2,
        players_max_with_expansions: 6,
        has_player_expansion: false
      };
      expect(formatPlayerCount(game)).toBe('2-4');
    });

    it('does not show asterisk when expMax does not extend baseMax', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_min_with_expansions: 2,
        players_max_with_expansions: 4,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('2-4');
    });

    it('does not show asterisk when expMax is less than baseMax', () => {
      const game = {
        players_min: 2,
        players_max: 4,
        players_min_with_expansions: 2,
        players_max_with_expansions: 3,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('2-4');
    });

    it('formats expanded equal min/max with asterisk', () => {
      const game = {
        players_min: 2,
        players_max: 2,
        players_min_with_expansions: 4,
        players_max_with_expansions: 4,
        has_player_expansion: true
      };
      expect(formatPlayerCount(game)).toBe('4*');
    });

    it('handles solo games', () => {
      const game = { players_min: 1, players_max: 1 };
      expect(formatPlayerCount(game)).toBe('1');
    });

    it('handles large player counts', () => {
      const game = { players_min: 4, players_max: 12 };
      expect(formatPlayerCount(game)).toBe('4-12');
    });
  });
});
