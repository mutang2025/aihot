import { Suspense } from "react";
import { Header } from "@/components/Header";

export function PageWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<><Header /><div className="p-6">加载中...</div></>}>{children}</Suspense>;
}
