"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { NewsCard } from "@/components/NewsCard";
import { api, NewsItem } from "@/lib/api";
import { format } from "date-fns";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function HomePage() {
  const params = useSearchParams();
  const featured = params.get("featured") === "1";
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listNews({
        featured_only: featured,
        since_hours: 168,
        limit: 50,
      });
      setNews(data);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [featured]);

  async function triggerScrape() {
    setRunning(true);
    try {
      await api.runScrape();
      setTimeout(load, 3000);
    } catch (e: any) {
      alert("触发抓取失败: " + e.message);
    } finally {
      setTimeout(() => setRunning(false), 5000);
    }
  }

  return (
    <>
      <Header />
      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold">
              {featured ? "精选" : "时间线"}
            </h1>
            <p className="text-sm text-neutral-500">
              {news.length} 条 · 更新于 {format(lastRefresh, "HH:mm:ss")}
            </p>
          </div>
          <button
            onClick={triggerScrape}
            disabled={running}
            className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-3 py-1.5 rounded transition-colors"
          >
            <RefreshCw size={14} className={running ? "animate-spin" : ""} />
            {running ? "抓取中..." : "立即抓取"}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 border border-amber-700 bg-amber-900/20 text-amber-200 rounded flex items-start gap-2 text-sm">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
            <div>
              <div>无法连接到后端: {error}</div>
              <div className="text-xs text-amber-400/70 mt-1">
                确认 backend 容器已启动, API 地址: {process.env.NEXT_PUBLIC_API_BASE}
              </div>
            </div>
          </div>
        )}

        {loading && news.length === 0 ? (
          <div className="text-center py-12 text-neutral-500">加载中...</div>
        ) : news.length === 0 ? (
          <div className="text-center py-12 text-neutral-500">
            {error ? "无法加载" : "还没有新闻。点击「立即抓取」试试。"}
          </div>
        ) : (
          <div className="grid gap-3">
            {news.map((n) => (
              <NewsCard key={n.id} news={n} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
