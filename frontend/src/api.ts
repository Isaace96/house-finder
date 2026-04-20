import { supabase } from "./supabaseClient";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeader()),
    ...((init.headers as Record<string, string>) || {}),
  };
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

export type Search = {
  id: number;
  query_url: string;
  search_type: string;
  label: string | null;
  sqm_min: number;
  sqm_max: number;
  max_pages: number;
  status: "pending" | "scraping" | "complete" | "failed";
  progress: number;
  error_message: string | null;
  total_found: number;
  created_at: string;
  updated_at: string;
};

export type Property = {
  id: number;
  rightmove_id: number;
  link: string;
  full_url: string;
  sqm: number | null;
  price: number | null;
  price_per_sqm: number | null;
  address: string | null;
  property_listing_type: string | null;
  status: "unreviewed" | "shortlisted" | "rejected";
};

export type Counts = {
  unreviewed: number;
  shortlisted: number;
  rejected: number;
};

export type Preview = {
  id: number;
  url: string;
  address: string;
  postcode: string;
  price: string;
  bedrooms: number | null;
  bathrooms: number | null;
  property_type: string | null;
  tenure: string | null;
  sqm: number | null;
  price_per_sqm: number | null;
  description: string;
  features: string[];
  images: { url: string; caption: string }[];
  floorplans: string[];
  stations: { name: string; distance: number | null; unit: string | null; types: string[] }[];
  agent: string | null;
};

export const api = {
  listSearches: () => apiFetch<Search[]>("/api/searches"),
  createSearch: (body: {
    query_url: string;
    search_type: "Sale" | "Rental";
    label?: string | null;
    sqm_min: number;
    sqm_max: number;
    max_pages: number;
  }) => apiFetch<Search>("/api/searches", { method: "POST", body: JSON.stringify(body) }),
  getSearch: (id: number) => apiFetch<Search>(`/api/searches/${id}`),
  deleteSearch: (id: number) => apiFetch<void>(`/api/searches/${id}`, { method: "DELETE" }),
  listProperties: (searchId: number, status?: string) => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    return apiFetch<Property[]>(
      `/api/searches/${searchId}/properties${qs.toString() ? `?${qs}` : ""}`,
    );
  },
  getCounts: (searchId: number) =>
    apiFetch<Counts>(`/api/searches/${searchId}/counts`),
  setStatus: (rightmoveId: number, status: string) =>
    apiFetch<void>(`/api/properties/${rightmoveId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  getPreview: (rightmoveId: number) =>
    apiFetch<Preview>(`/api/properties/${rightmoveId}/preview`),
};
