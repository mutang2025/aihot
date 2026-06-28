import type { Metadata } from "next";
import "./globals.css";
import { PageWrapper } from "@/components/PageWrapper";

export const metadata: Metadata = {
  title: "AIHOT - 每日 AI 热点",
  description: "由信源分级 + LLM 5维评分 + 公式重算驱动的 AI 行业资讯精选",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <PageWrapper>{children}</PageWrapper>
      </body>
    </html>
  );
}
