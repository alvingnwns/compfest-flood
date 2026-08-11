import { scenarioSchema } from "./src/domain/scenario";
import { z } from "zod";

async function main() {
  const res = await fetch("http://localhost:8000/api/scenarios/historical-jakarta");
  const data = await res.json();
  try {
    scenarioSchema.parse(data);
    console.log("Success! No Zod errors.");
  } catch (err) {
    if (err instanceof z.ZodError) {
      console.log(JSON.stringify(err.issues, null, 2));
    } else {
      console.error(err);
    }
  }
}
main();
