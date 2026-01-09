import React from "react";

export default function Pagination({ page, pageSize, total, onPage, showResultsCount = true }) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-xl p-3 sm:p-4 shadow-lg border border-white/50">
      <div className="flex flex-row items-center justify-between gap-2 sm:gap-3">
        {/* Results count */}
        {showResultsCount && (
          <div className="text-xs sm:text-sm text-slate-600 text-left shrink-0">
            <span className="font-bold text-emerald-600">
              {Math.min((page - 1) * pageSize + 1, total)}-{Math.min(page * pageSize, total)}
            </span>
            <span className="hidden sm:inline"> of{" "}</span>
            <span className="sm:hidden">/</span>
            <span className="font-bold text-emerald-600">{total}</span>
            <span className="hidden sm:inline"> games</span>
          </div>
        )}

        {/* Mobile-Optimized Pagination */}
        <nav aria-label="Game results pagination" className="flex items-center justify-center gap-1 sm:gap-2 shrink-0">
          {/* First page button - only show if not on first few pages */}
          {page > 3 && (
            <>
              <button
                onClick={() => onPage(1)}
                className="px-2 sm:px-3 py-2 text-sm border rounded hover:bg-emerald-50 min-h-10 sm:min-h-11 focus:outline-none focus:ring-2 focus:ring-emerald-300 transition-colors"
                aria-label="Go to first page"
              >
                1
              </button>
              <span className="text-slate-400 px-1" aria-hidden="true">...</span>
            </>
          )}

          {/* Previous button */}
          <button
            onClick={() => onPage(page - 1)}
            disabled={page <= 1}
            className="px-2 sm:px-3 py-2 text-sm border rounded disabled:opacity-50 hover:bg-emerald-50 min-h-10 sm:min-h-11 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-300 transition-colors"
            aria-label="Previous page"
          >
            <span className="hidden sm:inline">← Prev</span>
            <span className="sm:hidden" aria-hidden="true">←</span>
          </button>

          {/* Page numbers - show current and adjacent */}
          {Array.from({ length: Math.min(3, totalPages) }, (_, i) => {
            const pageNum = Math.max(1, page - 1) + i;
            if (pageNum > totalPages) return null;

            return (
              <button
                key={pageNum}
                onClick={() => onPage(pageNum)}
                className={`px-2 sm:px-3 py-2 text-sm rounded min-h-10 sm:min-h-11 focus:outline-none focus:ring-2 transition-colors ${
                  pageNum === page
                    ? "bg-emerald-500 text-white focus:ring-emerald-300"
                    : "border hover:bg-emerald-50 focus:ring-emerald-300"
                }`}
                aria-label={pageNum === page ? `Current page ${pageNum}` : `Go to page ${pageNum}`}
                aria-current={pageNum === page ? "page" : undefined}
              >
                {pageNum}
              </button>
            );
          })}

          {/* Next button */}
          <button
            onClick={() => onPage(page + 1)}
            disabled={page >= totalPages}
            className="px-2 sm:px-3 py-2 text-sm border rounded disabled:opacity-50 hover:bg-emerald-50 min-h-10 sm:min-h-11 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-300 transition-colors"
            aria-label="Next page"
          >
            <span className="hidden sm:inline">Next →</span>
            <span className="sm:hidden" aria-hidden="true">→</span>
          </button>

          {/* Last page button - only show if far from end */}
          {page < totalPages - 2 && (
            <>
              <span className="text-slate-400 px-1" aria-hidden="true">...</span>
              <button
                onClick={() => onPage(totalPages)}
                className="px-2 sm:px-3 py-2 text-sm border rounded hover:bg-emerald-50 min-h-10 sm:min-h-11 focus:outline-none focus:ring-2 focus:ring-emerald-300 transition-colors"
                aria-label="Go to last page"
              >
                {totalPages}
              </button>
            </>
          )}
        </nav>
      </div>
    </div>
  );
}