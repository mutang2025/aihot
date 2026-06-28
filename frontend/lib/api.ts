const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export interface NewsItem {
  id: number;
  source_id: number;
  source_name?: string;
  source_tier?: string;
  url: string;
  title: string;
  summary?: string;
  translated_title?: string;
  ai_summary?: string;
  category?: string;
  published_at?: string;
  fetched_at: string;
  final_score?: number;
  is_featured: boolean;
  cluster_id?: number;
  is_cluster_main: boolean;
  cluster_member_count?: number;
}

export interface Cluster {
  id: number;
  title: string;
  category?: string;
  member_count: number;
  top_score?: number;
  is_featured: boolean;
  first_seen_at: string;
  last_updated_at: string;
  main_news?: NewsItem;
  members?: NewsItem[];
}

export interface Digest {
  id: number;
  digest_date: string;
  sections: Record<string, any[]>;
  total_items: number;
  sent_feishu: boolean;
  sent_email: boolean;
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  health: () => fetchJSON<any>("/api/health"),
  listNews: (params: Record<string, any> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== "")
    ).toString();
    return fetchJSON<NewsItem[]>(`/api/news${qs ? "?" + qs : ""}`);
  },
  getNews: (id: number) => fetchJSON<NewsItem>(`/api/news/${id}`),
  getCluster: (id: number) => fetchJSON<Cluster>(`/api/clusters/${id}`),
  getLatestDigest: () => fetchJSON<Digest>("/api/digest/latest"),
  listSources: () => fetchJSON<any[]>("/api/sources"),
  submitFeedback: (payload: { news_id: number; rating: string; note?: string }) =>
    fetchJSON<any>("/api/feedback", { method: "POST", body: JSON.stringify(payload) }),
  runScrape: () => fetchJSON<any>("/api/admin/run-scrape", { method: "POST" }),
  runDigest: () => fetchJSON<any>("/api/admin/run-digest", { method: "POST" }),
};
