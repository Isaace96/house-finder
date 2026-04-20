import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Counts, type Property } from "../api";
import { PropertyCard } from "../components/PropertyCard";
import { PropertyModal } from "../components/PropertyModal";

const BUCKETS = ["unreviewed", "shortlisted", "rejected"] as const;
type Bucket = (typeof BUCKETS)[number];

export function ReviewPage() {
  const { id, bucket } = useParams();
  const searchId = Number(id);
  const currentBucket: Bucket = (BUCKETS as readonly string[]).includes(bucket || "")
    ? (bucket as Bucket)
    : "unreviewed";
  const qc = useQueryClient();
  const navigate = useNavigate();

  const search = useQuery({
    queryKey: ["search", searchId],
    queryFn: () => api.getSearch(searchId),
    refetchInterval: (q) => {
      const s = q.state.data;
      return s && (s.status === "scraping" || s.status === "pending") ? 3000 : false;
    },
  });

  const properties = useQuery<Property[]>({
    queryKey: ["properties", searchId, currentBucket],
    queryFn: () => api.listProperties(searchId, currentBucket),
  });

  const counts = useQuery<Counts>({
    queryKey: ["counts", searchId],
    queryFn: () => api.getCounts(searchId),
  });

  const setStatus = useMutation({
    mutationFn: ({ rm, status }: { rm: number; status: string }) => api.setStatus(rm, status),
    onMutate: async ({ rm }) => {
      await qc.cancelQueries({ queryKey: ["properties", searchId, currentBucket] });
      const prev = qc.getQueryData<Property[]>(["properties", searchId, currentBucket]);
      qc.setQueryData<Property[]>(
        ["properties", searchId, currentBucket],
        (old) => old?.filter((p) => p.rightmove_id !== rm) || [],
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(["properties", searchId, currentBucket], ctx.prev);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["counts", searchId] });
      qc.invalidateQueries({ queryKey: ["properties", searchId] });
    },
  });

  const [openId, setOpenId] = useState<number | null>(null);
  const cardRefs = useRef<Map<number, HTMLElement>>(new Map());
  const [focusedRm, setFocusedRm] = useState<number | null>(null);

  const setRef = (rm: number) => (el: HTMLElement | null) => {
    if (el) cardRefs.current.set(rm, el);
    else cardRefs.current.delete(rm);
  };

  useEffect(() => {
    if (properties.data && properties.data.length > 0 && focusedRm == null) {
      const first = properties.data[0].rightmove_id;
      const el = cardRefs.current.get(first);
      el?.focus();
      setFocusedRm(first);
    }
  }, [properties.data, focusedRm]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (openId != null) return;
      const target = e.target as HTMLElement;
      if (target && target.matches("input, textarea, select")) return;
      const list = properties.data || [];
      if (list.length === 0) return;
      const key = e.key.toLowerCase();
      const curIdx = list.findIndex((p) => p.rightmove_id === focusedRm);
      if (key === "j") {
        e.preventDefault();
        const next = list[Math.min(list.length - 1, (curIdx < 0 ? 0 : curIdx + 1))];
        cardRefs.current.get(next.rightmove_id)?.focus();
        cardRefs.current.get(next.rightmove_id)?.scrollIntoView({ block: "center", behavior: "smooth" });
        setFocusedRm(next.rightmove_id);
      } else if (key === "k") {
        e.preventDefault();
        const next = list[Math.max(0, curIdx - 1)];
        cardRefs.current.get(next.rightmove_id)?.focus();
        cardRefs.current.get(next.rightmove_id)?.scrollIntoView({ block: "center", behavior: "smooth" });
        setFocusedRm(next.rightmove_id);
      } else if (key === "o" || key === "enter") {
        if (focusedRm != null) {
          e.preventDefault();
          setOpenId(focusedRm);
        }
      } else if (key === "r" && currentBucket === "unreviewed" && focusedRm != null) {
        e.preventDefault();
        setStatus.mutate({ rm: focusedRm, status: "rejected" });
      } else if (key === "s" && currentBucket === "unreviewed" && focusedRm != null) {
        e.preventDefault();
        setStatus.mutate({ rm: focusedRm, status: "shortlisted" });
      } else if (key === "u" && currentBucket !== "unreviewed" && focusedRm != null) {
        e.preventDefault();
        setStatus.mutate({ rm: focusedRm, status: "unreviewed" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openId, properties.data, focusedRm, currentBucket, setStatus]);

  const handleAction = (rm: number, status: string) => {
    setStatus.mutate({ rm, status });
    if (openId === rm) setOpenId(null);
  };

  return (
    <main className="max-w-6xl mx-auto px-6 py-6">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/" className="text-sm text-blue-700 hover:underline">
          ← Searches
        </Link>
        <div className="font-semibold truncate">
          {search.data?.label || `Search #${searchId}`}
        </div>
        {search.data && (search.data.status === "scraping" || search.data.status === "pending") && (
          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
            Scraping {search.data.progress}%
          </span>
        )}
      </div>

      <nav className="flex gap-1 mb-4">
        {BUCKETS.map((b) => (
          <button
            key={b}
            onClick={() => navigate(`/searches/${searchId}/review/${b}`)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium ${
              b === currentBucket
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {b[0].toUpperCase() + b.slice(1)}
            <span className="ml-1 text-xs opacity-75">{counts.data?.[b] ?? 0}</span>
          </button>
        ))}
        <div className="ml-auto text-xs text-slate-500 flex items-center gap-2">
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">j</kbd>
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">k</kbd> nav ·
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">o</kbd> open ·
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">r</kbd> reject ·
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">s</kbd> shortlist ·
          <kbd className="px-1.5 py-0.5 bg-slate-200 rounded">u</kbd> undo
        </div>
      </nav>

      {properties.isLoading && <div className="text-slate-500">Loading…</div>}
      {properties.data && properties.data.length === 0 && (
        <div className="text-center py-24 text-slate-400">
          Nothing in <em>{currentBucket}</em>.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {properties.data?.map((p) => (
          <PropertyCard
            key={p.rightmove_id}
            ref={setRef(p.rightmove_id)}
            property={p}
            bucket={currentBucket}
            onOpen={setOpenId}
            onReject={(rm) => handleAction(rm, "rejected")}
            onShortlist={(rm) => handleAction(rm, "shortlisted")}
            onUndo={(rm) => handleAction(rm, "unreviewed")}
          />
        ))}
      </div>

      <PropertyModal
        rightmoveId={openId}
        bucket={currentBucket}
        onClose={() => setOpenId(null)}
        onReject={(rm) => handleAction(rm, "rejected")}
        onShortlist={(rm) => handleAction(rm, "shortlisted")}
        onUndo={(rm) => handleAction(rm, "unreviewed")}
      />
    </main>
  );
}
