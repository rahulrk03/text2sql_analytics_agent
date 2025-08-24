import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Text2SQL Analytics Agent",
  description: "Natural language to SQL queries with data analytics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
