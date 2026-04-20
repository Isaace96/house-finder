import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Preview } from "../api";

type Props = {
  rightmoveId: number | null;
  bucket: string;
  onClose: () => void;
  onReject: (rm: number) => void;
  onShortlist: (rm: number) => void;
  onUndo: (rm: number) => void;
};

export function PropertyModal({ rightmoveId, bucket, onClose, onReject, onShortlist, onUndo }: Props) {
  const { data, isLoading, error } = useQuery<Preview>({
    enabled: rightmoveId != null,
    queryKey: ["preview", rightmoveId],
    queryFn: () => api.getPreview(rightmoveId!),
  });

  const [idx, setIdx] = useState(0);
  useEffect(() => {
    setIdx(0);
  }, [rightmoveId]);

  useEffect(() => {
    if (rightmoveId == null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setIdx((i) => {
          const n = data?.images.length || 0;
          return n ? (i - 1 + n) % n : 0;
        });
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setIdx((i) => {
          const n = data?.images.length || 0;
          return n ? (i + 1) % n : 0;
        });
      } else if (e.key.toLowerCase() === "r" && bucket === "unreviewed") {
        e.preventDefault();
        onReject(rightmoveId);
      } else if (e.key.toLowerCase() === "s" && bucket === "unreviewed") {
        e.preventDefault();
        onShortlist(rightmoveId);
      } else if (e.key.toLowerCase() === "u" && bucket !== "unreviewed") {
        e.preventDefault();
        onUndo(rightmoveId);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rightmoveId, data, bucket, onClose, onReject, onShortlist, onUndo]);

  if (rightmoveId == null) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative mx-auto my-6 max-w-5xl max-h-[92vh] bg-white rounded-xl shadow-2xl flex flex-col">
        <header className="sticky top-0 z-10 bg-white border-b px-6 py-3 flex items-center gap-3 rounded-t-xl">
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-xl font-bold">{data?.price || ""}</span>
              <span className="text-sm text-slate-500">{data?.sqm ? `${data.sqm} m²` : ""}</span>
              {data?.price_per_sqm != null && (
                <span className="inline-block px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-xs font-medium">
                  £{Math.round(data.price_per_sqm).toLocaleString()}/m²
                </span>
              )}
              <span className="text-sm text-slate-500">
                {[
                  data?.bedrooms && `${data.bedrooms} bed`,
                  data?.bathrooms && `${data.bathrooms} bath`,
                  data?.property_type,
                  data?.tenure,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
            <div className="text-sm text-slate-700 truncate">{data?.address || ""}</div>
          </div>
          {data?.url && (
            <a
              href={data.url}
              target="_blank"
              rel="noopener"
              className="px-3 py-2 text-sm text-blue-700 hover:bg-blue-50 rounded-lg"
            >
              Rightmove ↗
            </a>
          )}
          {bucket === "unreviewed" ? (
            <>
              <button
                onClick={() => onReject(rightmoveId)}
                className="px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 text-sm font-medium rounded-lg"
              >
                Reject
              </button>
              <button
                onClick={() => onShortlist(rightmoveId)}
                className="px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-700 text-sm font-medium rounded-lg"
              >
                Shortlist
              </button>
            </>
          ) : (
            <button
              onClick={() => onUndo(rightmoveId)}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
            >
              Undo
            </button>
          )}
          <button
            onClick={onClose}
            aria-label="Close"
            className="ml-1 w-9 h-9 rounded-lg hover:bg-slate-100 text-slate-500 flex items-center justify-center text-lg"
          >
            ✕
          </button>
        </header>

        <div className="overflow-auto p-6 space-y-6">
          {isLoading && <div className="py-20 text-center text-slate-400">Loading…</div>}
          {error && (
            <div className="py-20 text-center text-red-600">
              {(error as Error).message}
            </div>
          )}
          {data && (
            <>
              <div>
                <div className="relative bg-slate-100 rounded-lg overflow-hidden aspect-[16/10]">
                  {data.images.length > 0 && (
                    <img src={data.images[idx]?.url} alt="" className="w-full h-full object-cover" />
                  )}
                  {data.images.length > 1 && (
                    <>
                      <button
                        onClick={() => setIdx((idx - 1 + data.images.length) % data.images.length)}
                        className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/70 text-white"
                      >
                        ‹
                      </button>
                      <button
                        onClick={() => setIdx((idx + 1) % data.images.length)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/70 text-white"
                      >
                        ›
                      </button>
                      <div className="absolute bottom-2 right-3 text-xs text-white bg-black/60 rounded px-2 py-0.5">
                        {idx + 1} / {data.images.length}
                      </div>
                    </>
                  )}
                </div>
                {data.images.length > 1 && (
                  <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
                    {data.images.map((im, i) => (
                      <img
                        key={i}
                        src={im.url}
                        loading="lazy"
                        onClick={() => setIdx(i)}
                        className={`h-16 w-24 object-cover rounded cursor-pointer flex-shrink-0 border-2 ${
                          i === idx ? "border-blue-500" : "border-transparent hover:border-blue-400"
                        }`}
                      />
                    ))}
                  </div>
                )}
              </div>

              {data.features.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 mb-2">
                    Key features
                  </h2>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-sm text-slate-800 list-disc pl-5">
                    {data.features.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </section>
              )}

              {data.description && (
                <section>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 mb-2">
                    Description
                  </h2>
                  <div
                    className="prose prose-sm max-w-none text-slate-800"
                    dangerouslySetInnerHTML={{ __html: data.description }}
                  />
                </section>
              )}

              {data.floorplans.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 mb-2">
                    Floorplan
                  </h2>
                  <div className="space-y-3">
                    {data.floorplans.map((src, i) => (
                      <img key={i} src={src} alt="Floorplan" className="max-w-full rounded border border-slate-200" />
                    ))}
                  </div>
                </section>
              )}

              {data.stations.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 mb-2">
                    Nearest stations
                  </h2>
                  <ul className="text-sm text-slate-800 space-y-1">
                    {data.stations.map((s, i) => (
                      <li key={i}>
                        {s.name}
                        {s.distance != null && ` — ${s.distance.toFixed(2)} ${s.unit || "miles"}`}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {data.agent && (
                <div className="text-xs text-slate-500 pt-4 border-t">
                  Marketed by {data.agent}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
