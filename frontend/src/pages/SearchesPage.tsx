import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { SearchCard } from "../components/SearchCard";
import { SearchForm } from "../components/SearchForm";

export function SearchesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["searches"],
    queryFn: api.listSearches,
    refetchInterval: (q) => {
      const list = q.state.data;
      const active = list?.some((s) => s.status === "scraping" || s.status === "pending");
      return active ? 3000 : false;
    },
  });

  return (
    <main className="max-w-6xl mx-auto px-6 py-8 grid gap-6 md:grid-cols-[320px,1fr]">
      <div>
        <SearchForm />
      </div>
      <div className="space-y-4">
        <h2 className="font-semibold">Your searches</h2>
        {isLoading && <div className="text-slate-500">Loading…</div>}
        {error && <div className="text-red-600">{(error as Error).message}</div>}
        {data && data.length === 0 && <div className="text-slate-500">No searches yet.</div>}
        <div className="grid gap-4 md:grid-cols-2">
          {data?.map((s) => (
            <SearchCard key={s.id} search={s} />
          ))}
        </div>
      </div>
    </main>
  );
}
