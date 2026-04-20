import { forwardRef } from "react";
import type { Property } from "../api";

type Props = {
  property: Property;
  bucket: string;
  onOpen: (rm: number) => void;
  onReject: (rm: number) => void;
  onShortlist: (rm: number) => void;
  onUndo: (rm: number) => void;
};

export const PropertyCard = forwardRef<HTMLElement, Props>(function PropertyCard(
  { property: p, bucket, onOpen, onReject, onShortlist, onUndo },
  ref,
) {
  const pps = p.price_per_sqm != null ? Math.round(p.price_per_sqm).toLocaleString() : null;
  return (
    <article
      ref={ref}
      tabIndex={0}
      id={`card-${p.rightmove_id}`}
      className="card bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col gap-3 outline-none focus:ring-4 focus:ring-blue-400 focus:ring-offset-2"
    >
      <div className="flex items-baseline justify-between">
        <div className="text-2xl font-bold">
          {p.price != null ? `£${p.price.toLocaleString()}` : "—"}
        </div>
        <div className="text-sm text-slate-500">{p.sqm != null ? `${p.sqm} m²` : ""}</div>
      </div>
      {pps && (
        <div className="text-sm">
          <span className="inline-block px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">
            £{pps}/m²
          </span>
        </div>
      )}
      <address className="text-sm text-slate-700 flex-1 not-italic whitespace-pre-line">
        {p.address || ""}
      </address>
      <div className="flex gap-2 pt-2 border-t border-slate-100">
        <button
          type="button"
          onClick={() => onOpen(p.rightmove_id)}
          className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded"
        >
          View →
        </button>
        {bucket === "unreviewed" ? (
          <>
            <button
              data-action="reject"
              onClick={() => onReject(p.rightmove_id)}
              className="px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 text-sm font-medium rounded"
            >
              Reject
            </button>
            <button
              data-action="shortlist"
              onClick={() => onShortlist(p.rightmove_id)}
              className="px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-700 text-sm font-medium rounded"
            >
              Shortlist
            </button>
          </>
        ) : (
          <button
            data-action="undo"
            onClick={() => onUndo(p.rightmove_id)}
            className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded"
          >
            Undo
          </button>
        )}
      </div>
    </article>
  );
});
