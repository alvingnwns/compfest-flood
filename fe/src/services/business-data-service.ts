import { businessImportResponseSchema } from "@/domain/business-data";
import { apiRequest, apiUrl } from "@/lib/api-client";

export const businessDataService = {
  templateUrl: apiUrl("/api/business-data/template"),
  importWorkbook: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest("/api/business-data/import", businessImportResponseSchema, {
      method: "POST",
      body: form,
    });
  },
  getSnapshot: (id: string) => apiRequest(`/api/business-data/${id}`, businessImportResponseSchema),
};
