/**
 * Tests for categoryStyles utility
 */
import { describe, it, expect } from 'vitest';
import {
  CATEGORY_STYLES,
  CATEGORY_GRADIENT_STYLES,
  getCategoryStyle
} from '../categoryStyles';

describe('categoryStyles', () => {
  describe('CATEGORY_STYLES (solid backgrounds)', () => {
    it('defines solid styles for all categories', () => {
      expect(CATEGORY_STYLES["GATEWAY_STRATEGY"]).toBe("bg-emerald-700 text-white border-emerald-800");
      expect(CATEGORY_STYLES["KIDS_FAMILIES"]).toBe("bg-purple-700 text-white border-purple-800");
      expect(CATEGORY_STYLES["CORE_STRATEGY"]).toBe("bg-blue-800 text-white border-blue-900");
      expect(CATEGORY_STYLES["COOP_ADVENTURE"]).toBe("bg-orange-700 text-white border-orange-800");
      expect(CATEGORY_STYLES["PARTY_ICEBREAKERS"]).toBe("bg-amber-800 text-white border-amber-900");
    });

    it('has a default fallback style', () => {
      expect(CATEGORY_STYLES.default).toBe("bg-slate-700 text-white border-slate-800");
    });

    it('includes all 5 categories plus default', () => {
      const keys = Object.keys(CATEGORY_STYLES);
      expect(keys).toHaveLength(6);
      expect(keys).toContain('default');
    });
  });

  describe('CATEGORY_GRADIENT_STYLES (gradient backgrounds)', () => {
    it('defines gradient styles for all categories', () => {
      expect(CATEGORY_GRADIENT_STYLES["GATEWAY_STRATEGY"]).toBe("bg-linear-to-r from-emerald-500 to-teal-500 text-white");
      expect(CATEGORY_GRADIENT_STYLES["KIDS_FAMILIES"]).toBe("bg-linear-to-r from-purple-500 to-pink-500 text-white");
      expect(CATEGORY_GRADIENT_STYLES["CORE_STRATEGY"]).toBe("bg-linear-to-r from-blue-600 to-indigo-600 text-white");
      expect(CATEGORY_GRADIENT_STYLES["COOP_ADVENTURE"]).toBe("bg-linear-to-r from-orange-500 to-red-500 text-white");
      expect(CATEGORY_GRADIENT_STYLES["PARTY_ICEBREAKERS"]).toBe("bg-linear-to-r from-yellow-500 to-amber-500 text-white");
    });

    it('has a default fallback gradient style', () => {
      expect(CATEGORY_GRADIENT_STYLES.default).toBe("bg-linear-to-r from-slate-500 to-gray-500 text-white");
    });

    it('includes all 5 categories plus default', () => {
      const keys = Object.keys(CATEGORY_GRADIENT_STYLES);
      expect(keys).toHaveLength(6);
      expect(keys).toContain('default');
    });
  });

  describe('getCategoryStyle()', () => {
    describe('solid backgrounds (default)', () => {
      it('returns correct solid style for GATEWAY_STRATEGY', () => {
        expect(getCategoryStyle("GATEWAY_STRATEGY")).toBe("bg-emerald-700 text-white border-emerald-800");
      });

      it('returns correct solid style for KIDS_FAMILIES', () => {
        expect(getCategoryStyle("KIDS_FAMILIES")).toBe("bg-purple-700 text-white border-purple-800");
      });

      it('returns correct solid style for CORE_STRATEGY', () => {
        expect(getCategoryStyle("CORE_STRATEGY")).toBe("bg-blue-800 text-white border-blue-900");
      });

      it('returns correct solid style for COOP_ADVENTURE', () => {
        expect(getCategoryStyle("COOP_ADVENTURE")).toBe("bg-orange-700 text-white border-orange-800");
      });

      it('returns correct solid style for PARTY_ICEBREAKERS', () => {
        expect(getCategoryStyle("PARTY_ICEBREAKERS")).toBe("bg-amber-800 text-white border-amber-900");
      });

      it('returns default solid style for unknown category', () => {
        expect(getCategoryStyle("UNKNOWN_CATEGORY")).toBe("bg-slate-700 text-white border-slate-800");
      });

      it('returns default solid style for null category', () => {
        expect(getCategoryStyle(null)).toBe("bg-slate-700 text-white border-slate-800");
      });

      it('returns default solid style for undefined category', () => {
        expect(getCategoryStyle(undefined)).toBe("bg-slate-700 text-white border-slate-800");
      });

      it('returns default solid style for empty string', () => {
        expect(getCategoryStyle("")).toBe("bg-slate-700 text-white border-slate-800");
      });
    });

    describe('gradient backgrounds (gradient=true)', () => {
      it('returns correct gradient style for GATEWAY_STRATEGY', () => {
        expect(getCategoryStyle("GATEWAY_STRATEGY", true)).toBe("bg-linear-to-r from-emerald-500 to-teal-500 text-white");
      });

      it('returns correct gradient style for KIDS_FAMILIES', () => {
        expect(getCategoryStyle("KIDS_FAMILIES", true)).toBe("bg-linear-to-r from-purple-500 to-pink-500 text-white");
      });

      it('returns correct gradient style for CORE_STRATEGY', () => {
        expect(getCategoryStyle("CORE_STRATEGY", true)).toBe("bg-linear-to-r from-blue-600 to-indigo-600 text-white");
      });

      it('returns correct gradient style for COOP_ADVENTURE', () => {
        expect(getCategoryStyle("COOP_ADVENTURE", true)).toBe("bg-linear-to-r from-orange-500 to-red-500 text-white");
      });

      it('returns correct gradient style for PARTY_ICEBREAKERS', () => {
        expect(getCategoryStyle("PARTY_ICEBREAKERS", true)).toBe("bg-linear-to-r from-yellow-500 to-amber-500 text-white");
      });

      it('returns default gradient style for unknown category', () => {
        expect(getCategoryStyle("UNKNOWN_CATEGORY", true)).toBe("bg-linear-to-r from-slate-500 to-gray-500 text-white");
      });

      it('returns default gradient style for null category', () => {
        expect(getCategoryStyle(null, true)).toBe("bg-linear-to-r from-slate-500 to-gray-500 text-white");
      });

      it('returns default gradient style for undefined category', () => {
        expect(getCategoryStyle(undefined, true)).toBe("bg-linear-to-r from-slate-500 to-gray-500 text-white");
      });
    });

    describe('gradient parameter variations', () => {
      it('uses solid styles when gradient is false', () => {
        expect(getCategoryStyle("GATEWAY_STRATEGY", false)).toBe("bg-emerald-700 text-white border-emerald-800");
      });

      it('uses solid styles when gradient is omitted (default)', () => {
        expect(getCategoryStyle("GATEWAY_STRATEGY")).toBe("bg-emerald-700 text-white border-emerald-800");
      });

      it('uses gradient styles when gradient is true', () => {
        expect(getCategoryStyle("GATEWAY_STRATEGY", true)).toBe("bg-linear-to-r from-emerald-500 to-teal-500 text-white");
      });
    });
  });
});
