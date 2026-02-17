import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Podcast UI Editor",
  description: "Podcast RSS editor",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        {children}
      </body>
    </html>
  );
}
