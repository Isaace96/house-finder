import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

export function SearchForm() {
  const qc = useQueryClient();
  const [queryUrl, setQueryUrl] = useState("");
  const [label, setLabel] = useState("");
  const [searchType, setSearchType] = useState<"Sale" | "Rental">("Sale");
  const [sqmMin, setSqmMin] = useState(70);
  const [sqmMax, setSqmMax] = useState(180);
  const [maxPages, setMaxPages] = useState(10);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: api.createSearch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["searches"] });
      setQueryUrl("");
      setLabel("");
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      query_url: queryUrl,
      search_type: searchType,
      label: label || null,
      sqm_min: sqmMin,
      sqm_max: sqmMax,
      max_pages: maxPages,
    });
  };

  return (
    <form onSubmit={onSubmit} className="bg-white p-5 rounded-xl border border-slate-200 space-y-3">
      <h2 className="font-semibold">New search</h2>
      <input
        type="url"
        required
        placeholder="Rightmove search URL"
        value={queryUrl}
        onChange={(e) => setQueryUrl(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
      />
      <input
        type="text"
        placeholder="Label (optional)"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 rounded text-sm"
      />
      <div className="grid grid-cols-2 gap-3 text-sm">
        <label className="flex flex-col gap-1">
          Type
          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value as "Sale" | "Rental")}
            className="px-3 py-2 border border-slate-300 rounded"
          >
            <option value="Sale">Sale</option>
            <option value="Rental">Rental</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Max pages
          <input
            type="number"
            min={1}
            max={42}
            value={maxPages}
            onChange={(e) => setMaxPages(parseInt(e.target.value || "1", 10))}
            className="px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="flex flex-col gap-1">
          sqm min
          <input
            type="number"
            value={sqmMin}
            onChange={(e) => setSqmMin(parseFloat(e.target.value))}
            className="px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="flex flex-col gap-1">
          sqm max
          <input
            type="number"
            value={sqmMax}
            onChange={(e) => setSqmMax(parseFloat(e.target.value))}
            className="px-3 py-2 border border-slate-300 rounded"
          />
        </label>
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded disabled:opacity-50"
      >
        {mutation.isPending ? "Creating…" : "Start search"}
      </button>
    </form>
  );
}
