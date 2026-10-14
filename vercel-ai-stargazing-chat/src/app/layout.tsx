import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Nova - Lantern Ridge night-sky assistant",
  description: "Streaming observing assistant, traced with Opik",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          background: "#0e1224",
          color: "#e8ebf5",
        }}
      >
        {children}
      </body>
    </html>
  );
}
