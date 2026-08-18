import type { Metadata } from "next";
import { AppProviders } from "@/components/providers/app-providers";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResiliChain AI",
  description: "Sistem pendukung keputusan pemulihan rantai pasok berbasis risiko banjir",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body className="font-sans"><AppProviders>{children}</AppProviders></body></html>;
}
