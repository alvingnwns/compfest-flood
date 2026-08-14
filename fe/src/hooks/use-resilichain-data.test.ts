import { describe, expect, it } from "vitest";
import { simulationQueryKey } from "./use-resilichain-data";

describe("simulation query identity", () => {
  it("does not reuse results when the backend returns a different scenario identity", () => {
    expect(simulationQueryKey("sim-q1-normal")).not.toEqual(simulationQueryKey("sim-q3-normal"));
    expect(simulationQueryKey("sim-q3-normal")).not.toEqual(simulationQueryKey("sim-q3-critical-stock"));
  });
});
