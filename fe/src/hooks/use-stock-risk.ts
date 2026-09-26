"use client";

import { useQuery } from "@tanstack/react-query";
import { stockRiskService } from "@/services/stock-risk-service";

export const stockRiskQueryKey = ["inventory", "stock-risk"] as const;

export const useStockRisk = () =>
  useQuery({ queryKey: stockRiskQueryKey, queryFn: stockRiskService.getOverview });
