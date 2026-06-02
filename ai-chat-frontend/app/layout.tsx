import "./globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AI Chat Platform",
  description: "Chat con Hugging Face + FastAPI",
  icons: {
    icon: [
      {
        url: "/icon.svg?v=ai-brain-2",
        type: "image/svg+xml",
        sizes: "any",
      },
    ],
    shortcut: "/icon.svg?v=ai-brain-2",
  },
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
