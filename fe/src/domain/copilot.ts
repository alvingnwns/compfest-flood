import { z } from "zod";

export const copilotConversationMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(2_000),
});

export const copilotProviderSchema = z.enum(["gemini", "qwen", "deterministic"]);

export const persistedCopilotMessageSchema = copilotConversationMessageSchema.extend({
  provider: copilotProviderSchema.optional(),
  grounded: z.literal(true).optional(),
}).strict();

export const persistedCopilotThreadSchema = z.object({
  version: z.literal(1),
  messages: z.array(persistedCopilotMessageSchema).max(40),
  suggestedQuestions: z.array(z.string().min(1).max(1_000)).max(6),
}).strict();

export const copilotRequestSchema = z.object({
  message: z.string().trim().min(1).max(1_000),
  recentMessages: z.array(copilotConversationMessageSchema).max(6).default([]),
});

export const copilotResponseSchema = z.object({
  answer: z.string().min(1),
  provider: copilotProviderSchema,
  grounded: z.literal(true),
  suggestedQuestions: z.array(z.string()),
  fallbackReason: z.string().optional(),
});

export type CopilotConversationMessage = z.infer<typeof copilotConversationMessageSchema>;
export type CopilotProvider = z.infer<typeof copilotProviderSchema>;
export type PersistedCopilotMessage = z.infer<typeof persistedCopilotMessageSchema>;
export type PersistedCopilotThread = z.infer<typeof persistedCopilotThreadSchema>;
export type CopilotRequest = z.infer<typeof copilotRequestSchema>;
export type CopilotResponse = z.infer<typeof copilotResponseSchema>;
