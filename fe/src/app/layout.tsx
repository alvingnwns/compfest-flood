import type { Metadata } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";
import { AppProviders } from "@/components/providers/app-providers";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "ResiliChain AI",
  description: "Sistem pendukung keputusan pemulihan rantai pasok berbasis risiko banjir",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body className={`${geist.variable} ${mono.variable} font-sans`}><AppProviders>{children}</AppProviders></body></html>;
}
