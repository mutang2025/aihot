import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import { NewsItem } from "@/lib/api";
import { clsx } from "clsx";

const TIER_STYLES: Record<string, string> = {
  T1: "bg-amber-500/20 text-amber-300 border-amber-700",
  "T1.5": "bg-purple-500/20 text-purple-300 border-purple-700",
  T2: "bg-neutral-700/30 text-neutral-400 border-neutral-600",
};

const CAT_LABELS: Record<string, string> = {
  model_release: "模型",
  product_release: "产品",
  industry: "行业",
  research: "研究",
  tips_opinions: "观点",
  unknown: "其他",
};

export function NewsCard({ news }: { news: NewsItem }) {
  const title = news.translated_title || news.title;
  const date = news.published_at || news.fetched_at;
  return (
    <article className="border border-neutral-800 rounded-lg p-4 hover:border-blue-500/50 transition-colors bg-neutral-900/40">
      <div className="flex items-center gap-2 text-xs text-neutral-500 mb-2">
        {news.source_tier && (
          <span className={clsx("px-1.5 py-0.5 border rounded", TIER_STYLES[news.source_tier] || TIER_STYLES.T2)}>
            {news.source_tier}
          </span>
        )}
        {news.category && (
          <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-300 border border-blue-800/50 rounded">
            {CAT_LABELS[news.category] || news.category}
          </span>
        )}
        <span>{news.source_name}</span>
        {news.final_score != null && (
          <span className="ml-auto font-mono text-neutral-400">★ {news.final_score.toFixed(1)}</span>
        )}
        {news.is_featured && (
          <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-700 rounded">
            精选
          </span>
        )}
      </div>
      <h3 className="text-lg font-medium leading-snug mb-1">
        {news.cluster_id && news.is_cluster_main && news.cluster_member_count && news.cluster_member_count > 1 ? (
          <Link href={`/news/${news.id}`}>
            {title}
            {news.translated_title && news.title !== news.translated_title && (
              <span className="ml-2 text-xs text-neutral-500">
                (+{news.cluster_member_count - 1} 相关报道)
              </span>
            )}
            {news.translated_title && news.title !== news.translated_title && (
              <div className="text-xs text-neutral-600 mt-1 font-normal line-clamp-1">
                EN: {news.title}
              </div>
            )}
          </Link>
        ) : (
          <a href={news.url} target="_blank" rel="noopener noreferrer">
            {title}
            {news.translated_title && news.title !== news.translated_title && (
              <div className="text-xs text-neutral-600 mt-1 font-normal line-clamp-1">
                EN: {news.title}
              </div>
            )}
          </a>
        )}
      </h3>
      {news.ai_summary && (
        <p className="text-sm text-neutral-400 mt-1.5 line-clamp-2">{news.ai_summary}</p>
      )}
      {news.summary && !news.ai_summary && (
        <p className="text-sm text-neutral-500 mt-1.5 line-clamp-2 italic opacity-70">{news.summary}</p>
      )}
      <div className="flex items-center justify-between mt-2 text-xs text-neutral-600">
        <span>
          {date ? formatDistanceToNow(new Date(date), { addSuffix: true, locale: zhCN }) : "—"}
        </span>
        {news.cluster_id && news.cluster_member_count && news.cluster_member_count > 1 && (
          <Link href={`/news/${news.id}`} className="text-blue-400 hover:underline">
            查看聚类 →
          </Link>
        )}
      </div>
    </article>
  );
}
