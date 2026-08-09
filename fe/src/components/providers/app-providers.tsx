"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { publicEnv } from "@/config/public-env";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false } } });

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(publicEnv.NEXT_PUBLIC_DATA_SOURCE !== "mock");

  useEffect(() => {
    if (publicEnv.NEXT_PUBLIC_DATA_SOURCE !== "mock") return;
    void import("@/mocks/browser").then(({ worker }) => worker.start({ onUnhandledRequest: "bypass" })).then(() => setReady(true));
  }, []);

  return <QueryClientProvider client={queryClient}>{ready ? children : <div className="grid min-h-screen place-items-center bg-background"><div className="text-center"><div className="mx-auto mb-3 h-7 w-7 animate-spin rounded-full border-2 border-outline border-t-primary" /><p className="text-sm text-muted">Preparing historical snapshot…</p></div></div>}</QueryClientProvider>;
}
