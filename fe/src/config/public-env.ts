import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_DATA_SOURCE: z.enum(["mock", "api"]).default("api"),
  NEXT_PUBLIC_API_BASE_URL: z.string().default("http://localhost:8000").transform((value) => value.replace(/\/+$/, "")),
}).superRefine((value, context) => {
  if (value.NEXT_PUBLIC_DATA_SOURCE === "api") {
    try { new URL(value.NEXT_PUBLIC_API_BASE_URL); }
    catch { context.addIssue({ code: "custom", path: ["NEXT_PUBLIC_API_BASE_URL"], message: "A valid absolute API base URL is required in api mode" }); }
  }
});

export const publicEnv = publicEnvSchema.parse({
  NEXT_PUBLIC_DATA_SOURCE: process.env.NEXT_PUBLIC_DATA_SOURCE,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
});
