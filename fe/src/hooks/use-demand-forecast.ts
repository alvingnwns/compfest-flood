"use client";
import { useQuery } from "@tanstack/react-query";
import { demandForecastService } from "@/services/demand-forecast-service";
export const demandForecastQueryKey = ["inventory-demand", "forecast"] as const;
export const useDemandForecast = (productId?: string) => useQuery({ queryKey: [...demandForecastQueryKey, productId], queryFn: () => demandForecastService.getForecast(productId) });
