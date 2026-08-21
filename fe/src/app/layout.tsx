import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import { AppProviders } from "@/components/providers/app-providers";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  variable: "--font-montserrat",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ARUNA",
  description: "Sistem pendukung keputusan pemulihan rantai pasok berbasis risiko banjir",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" className={montserrat.variable}>
      <body className={`${montserrat.className} font-sans`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}

