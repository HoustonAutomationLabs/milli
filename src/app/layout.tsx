import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Milli — Casework Dashboard",
  description:
    "Role-based casework dashboard for a Texas foster-care agency, reading from ExtendedReach via Zoho Analytics.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
