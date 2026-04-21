import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Search } from "../api";

const statusStyle: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  scraping: "bg-blue-100 text-blue-700",
  complete: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export function SearchCard({ search }: { search: Search }) {
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: () => api.deleteSearch(search.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["searches"] }),
  });
  const rerun = useMutation({
    mutationFn: () => api.rerunSearch(search.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["searches"] }),
  });
  const canRerun = search.status === "complete" || search.status === "failed";

  return (
    <article className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-semibold truncate">
            {search.label || `Search #${search.id}`}
          </div>
          <div className="text-xs text-slate-500 truncate" title={search.query_url}>
            {search.query_url}
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusStyle[search.status] || ""}`}>
          {search.status}
        </span>
      </div>
      <div className="text-xs text-slate-600 flex gap-3 flex-wrap">
        <span>{search.search_type}</span>
        <span>{search.sqm_min}–{search.sqm_max} m²</span>
        <span>{search.max_pages} pages</span>
        <span>{search.total_found} found</span>
        {search.total_failed > 0 && (
          <span className="text-amber-600">{search.total_failed} skipped</span>
        )}
      </div>
      {(search.status === "scraping" || search.status === "pending") && (
        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
          <div className="bg-blue-500 h-full transition-all" style={{ width: `${search.progress}%` }} />
        </div>
      )}
      {search.error_message && (
        <div className="text-xs text-red-600">{search.error_message}</div>
      )}
      <div className="flex gap-2 pt-2 border-t border-slate-100">
        <Link
          to={`/searches/${search.id}/review`}
          className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded text-center"
        >
          Review →
        </Link>
        <button
          onClick={() => rerun.mutate()}
          disabled={!canRerun || rerun.isPending}
          className="px-3 py-2 bg-slate-100 hover:bg-blue-100 hover:text-blue-700 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed"
          title={canRerun ? "Rerun scrape to pick up new listings" : "Already running"}
        >
          {rerun.isPending ? "Rerunning…" : "Rerun"}
        </button>
        <button
          onClick={() => {
            if (confirm("Delete this search?")) del.mutate();
          }}
          className="px-3 py-2 bg-slate-100 hover:bg-red-100 hover:text-red-700 text-sm rounded"
        >
          Delete
        </button>
      </div>
    </article>
  );
}
