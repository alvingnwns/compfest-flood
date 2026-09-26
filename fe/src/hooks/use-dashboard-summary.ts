"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/services/dashboard-service";

export const dashboardSummaryQueryKey = ["inventory-dashboard", "summary"] as const;

export const useDashboardSummary = () =>
  useQuery({
    queryKey: dashboardSummaryQueryKey,
    queryFn: dashboardService.getSummary,
  });
