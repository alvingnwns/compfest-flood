"use client";

import { useQuery } from "@tanstack/react-query";
import { salesService } from "@/services/sales-service";

export const salesOverviewQueryKey = ["inventory-sales", "overview"] as const;

export const useSalesOverview = () =>
  useQuery({ queryKey: salesOverviewQueryKey, queryFn: salesService.getOverview });

export const useSalesTransaction = (id?: string) => useQuery({ queryKey: ["inventory-sales", "transaction", id], queryFn: () => salesService.getTransaction(id!), enabled: !!id });
