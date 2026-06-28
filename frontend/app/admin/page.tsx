"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { api } from "@/lib/api";
import { Play, Database, ListChecks, AlertCircle } from "lucide-react";

export default function AdminPage() {
  const [health, setHealth] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);
  const [actionStatus, setActionStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const h = await api.health();
      setHealth(h);
      const s = await api.listSources();
      setSources(s);
    } catch (e: any) {
      setActionStatus("无法连接后端: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function action(name: string, fn: () => Promise<any>) {
    setActionStatus(`${name} 中...`);
    try {
      await fn();
      setActionStatus(`${name} 已触发, 等待几秒后刷新`);
      setTimeout(load, 5000);
    } catch (e: any) {
      setActionStatus(`${name} 失败: ${e.message}`);
    }
  }

  return (
    <>
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="text-2xl font-semibold mb-6">后台管理</h1>

        {actionStatus && (
          <div className="mb-4 p-3 bg-neutral-900 border border-neutral-800 rounded text-sm">
            {actionStatus}
          </div>
        )}

        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Database size={18} /> 系统状态
          </h2>
          {loading || !health ? (
            <div className="text-neutral-500">加载中...</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Stat label="版本" value={health.version} />
              <Stat label="信源数 (启用)" value={health.sources_enabled} />
              <Stat label="新闻总数" value={health.news_total} />
              <Stat label="精选数" value={health.news_featured} />
            </div>
          )}
        </section>

        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Play size={18} /> 手动操作
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => action("立即抓取", api.runScrape)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
            >
              立即抓取一轮
            </button>
            <button
              onClick={() => action("生成日报", api.runDigest)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm"
            >
              生成并发送日报
            </button>
            <button
              onClick={load}
              className="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 rounded text-sm"
            >
              刷新状态
            </button>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <ListChecks size={18} /> 信源清单 ({sources.length})
          </h2>
          {sources.length === 0 ? (
            <div className="text-neutral-500 text-sm">没有信源。请确认 sources.yaml 已加载。</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-neutral-400 border-b border-neutral-800">
                  <tr>
                    <th className="text-left py-2 px-2">等级</th>
                    <th className="text-left py-2 px-2">名称</th>
                    <th className="text-left py-2 px-2">分类</th>
                    <th className="text-left py-2 px-2">类型</th>
                    <th className="text-left py-2 px-2">启用</th>
                    <th className="text-left py-2 px-2">最近抓取</th>
                    <th className="text-left py-2 px-2">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s) => (
                    <tr key={s.id} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                      <td className="py-2 px-2 font-mono text-xs">{s.tier}</td>
                      <td className="py-2 px-2">{s.name}</td>
                      <td className="py-2 px-2 text-neutral-400">{s.category}</td>
                      <td className="py-2 px-2 text-neutral-400">{s.scraper_type}</td>
                      <td className="py-2 px-2">{s.enabled ? "✓" : "✗"}</td>
                      <td className="py-2 px-2 text-neutral-500 text-xs">
                        {s.last_fetched_at ? new Date(s.last_fetched_at).toLocaleString("zh-CN") : "—"}
                      </td>
                      <td className="py-2 px-2 text-xs">
                        {s.last_status === "ok" ? <span className="text-green-400">OK</span>
                          : s.last_status === "error" ? <span className="text-red-400" title={s.last_error}>ERR</span>
                          : <span className="text-neutral-500">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mt-8 p-4 border border-amber-800/50 bg-amber-900/10 rounded text-sm">
          <div className="flex items-start gap-2">
            <AlertCircle size={16} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-amber-300 mb-1">鉴权提示</div>
              <p className="text-amber-200/80 text-xs">
                当前后台无登录鉴权 (主人 v1 默认推荐: 公开访问前台 + basic auth 后台)。
                生产环境建议:
                (1) 在 reverse proxy (nginx/caddy) 上对 /admin 加 basic auth;
                (2) 或在 .env 设置 ADMIN_USER/ADMIN_PASS 后启用内置鉴权 (待开发)。
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="border border-neutral-800 rounded p-3 bg-neutral-900/50">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="text-2xl font-mono mt-1">{value}</div>
    </div>
  );
}
