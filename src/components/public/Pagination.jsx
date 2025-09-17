import React from "react";

export default function Pagination({ page, pageSize, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const prev = () => onPage(Math.max(1, page - 1));
  const next = () => onPage(Math.min(pages, page + 1));
  
  const hasPrev = page > 1;
  const hasNext = page < pages;

  return (
    <nav aria-label="Game pagination" className="flex flex-col sm:flex-row items-center justify-between gap-4">
      {/* Previous Button */}
      <button
        onClick={prev}
        disabled={!hasPrev}
        aria-label={hasPrev ? `Go to previous page (page ${page - 1} of ${pages})` : "No previous page available"}
        className="group flex items-center px-6 py-3 rounded-xl border-2 border-slate-200 hover:border-emerald-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
      >
        <svg 
          className="w-4 h-4 mr-2 transition-transform group-hover:-translate-x-1 group-disabled:group-hover:translate-x-0" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span className="font-medium">Previous</span>
      </button>

      {/* Page Info */}
      <div className="flex items-center space-x-2">
        <span className="text-slate-600">Page</span>
        <span 
          className="px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg font-bold"
          aria-label={`Current page ${page}`}
        >
          {page}
        </span>
        <span className="text-slate-600">of</span>
        <span 
          className="px-3 py-2 bg-slate-100 rounded-lg font-bold text-slate-700"
          aria-label={`Total pages ${pages}`}
        >
          {pages}
        </span>
        <span className="text-slate-500 text-sm" aria-label={`Total games ${total}`}>
          ({total} games)
        </span>
      </div>

      {/* Next Button */}
      <button
        onClick={next}
        disabled={!hasNext}
        aria-label={hasNext ? `Go to next page (page ${page + 1} of ${pages})` : "No next page available"}
        className="group flex items-center px-6 py-3 rounded-xl border-2 border-slate-200 hover:border-emerald-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
      >
        <span className="font-medium">Next</span>
        <svg 
          className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1 group-disabled:group-hover:translate-x-0" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </nav>
  );
}