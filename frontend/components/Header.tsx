import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-50 bg-neutral-950/80 backdrop-blur border-b border-neutral-800">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          AIHOT
          <span className="text-sm font-normal text-neutral-400 hidden sm:inline">
            每日 AI 热点
          </span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="hover:text-blue-400">时间线</Link>
          <Link href="/?featured=1" className="hover:text-blue-400">精选</Link>
          <Link href="/admin" className="hover:text-blue-400 text-neutral-500">管理</Link>
        </nav>
      </div>
    </header>
  );
}
