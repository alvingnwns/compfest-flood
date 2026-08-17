import { z } from "zod";

export const copilotConversationMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(2_000),
});

export const copilotRequestSchema = z.object({
  message: z.string().trim().min(1).max(1_000),
  recentMessages: z.array(copilotConversationMessageSchema).max(6).default([]),
});

export const copilotResponseSchema = z.object({
  answer: z.string().min(1),
  provider: z.enum(["gemini", "qwen", "deterministic"]),
  grounded: z.literal(true),
  suggestedQuestions: z.array(z.string()),
  fallbackReason: z.string().optional(),
});

export type CopilotConversationMessage = z.infer<typeof copilotConversationMessageSchema>;
export type CopilotRequest = z.infer<typeof copilotRequestSchema>;
export type CopilotResponse = z.infer<typeof copilotResponseSchema>;
