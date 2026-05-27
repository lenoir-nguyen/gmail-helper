import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gmail Helper",
  description: "Extract Gmail data into your documents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
