"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { NewsCard } from "@/components/NewsCard";
import { api, Cluster, NewsItem } from "@/lib/api";
import { ArrowLeft, ThumbsUp, ThumbsDown } from "lucide-react";

export default function NewsDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = parseInt(params.id, 10);
  const [cluster, setCluster] = useState<Cluster | null>(null);
  const [news, setNews] = useState<NewsItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .getNews(id)
      .then(async (n) => {
        setNews(n);
        if (n.cluster_id) {
          try {
            const c = await api.getCluster(n.cluster_id);
            setCluster(c);
          } catch {
            // cluster not available
          }
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function feedback(rating: "good" | "bad") {
    if (!news) return;
    try {
      await api.submitFeedback({ news_id: news.id, rating });
      alert("已记录，谢谢反馈！");
    } catch (e: any) {
      alert("反馈失败: " + e.message);
    }
  }

  if (loading) {
    return (
      <>
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8 text-neutral-500">加载中...</main>
      </>
    );
  }
  if (error || !news) {
    return (
      <>
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <button onClick={() => router.back()} className="text-sm text-blue-400 mb-4">
            ← 返回
          </button>
          <div className="text-amber-400">未找到新闻: {error}</div>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-6">
        <button onClick={() => router.back()} className="text-sm text-blue-400 mb-4 inline-flex items-center gap-1">
          <ArrowLeft size={14} /> 返回
        </button>

        <article className="mb-8">
          <h1 className="text-3xl font-semibold mb-2 leading-tight">
            {news.translated_title || news.title}
          </h1>
          {news.translated_title && (
            <p className="text-neutral-500 text-sm mb-3">原文: {news.title}</p>
          )}
          {news.ai_summary && (
            <div className="p-4 bg-blue-500/10 border border-blue-800/50 rounded mb-4">
              <div className="text-xs text-blue-300 mb-1">AI 摘要</div>
              <p className="text-sm leading-relaxed">{news.ai_summary}</p>
            </div>
          )}
          <div className="flex items-center gap-3 text-sm text-neutral-400 mb-3">
            <span>{news.source_name}</span>
            {news.source_tier && <span>· {news.source_tier}</span>}
            {news.category && <span>· {news.category}</span>}
            {news.final_score != null && <span>· 评分 {news.final_score.toFixed(1)}</span>}
          </div>
          <a
            href={news.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
          >
            查看原文 →
          </a>
          <div className="mt-4 flex items-center gap-2 text-sm">
            <span className="text-neutral-500">这条精选得对吗?</span>
            <button
              onClick={() => feedback("good")}
              className="flex items-center gap-1 px-2 py-1 bg-green-700/30 hover:bg-green-700/50 border border-green-800 rounded"
            >
              <ThumbsUp size={14} /> 对
            </button>
            <button
              onClick={() => feedback("bad")}
              className="flex items-center gap-1 px-2 py-1 bg-red-700/30 hover:bg-red-700/50 border border-red-800 rounded"
            >
              <ThumbsDown size={14} /> 错
            </button>
          </div>
        </article>

        {cluster && cluster.members && cluster.members.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">
              相关报道 ({cluster.member_count} 条)
            </h2>
            <p className="text-sm text-neutral-500 mb-4">
              同一事件被多个来源报道, 聚类展示.
            </p>
            <div className="grid gap-3">
              {cluster.members.map((m) => (
                <NewsCard key={m.id} news={m} />
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
