import { Suspense } from "react";
import { CopilotPage } from "@/features/copilot/copilot-page";

export default function Page() {
  return <Suspense><CopilotPage /></Suspense>;
}
