// The real opik and opik-openai packages with tracking disabled
// (OPIK_TRACK_DISABLE=true, set in vitest.config.ts): the wrapper must not
// get in the way of a stubbed images call.
import { describe, expect, it, vi } from "vitest";
import { Opik } from "opik";
import { trackOpenAI } from "opik-openai";

describe("traced image call with tracking disabled", () => {
  it("passes the request through and returns the stubbed image", async () => {
    const generate = vi.fn(async () => ({ data: [{ b64_json: "AAAA" }] }));
    const stub: any = { images: { generate } };

    const opik = new Opik({ projectName: "unit-test" });
    const trace = opik.trace({ name: "generate-plate", input: { species: "x" } });
    const tracked = trackOpenAI(stub, { client: opik, parent: trace });

    const res = await tracked.images.generate({
      model: "gpt-image-1", prompt: "a wren", n: 1, size: "1024x1024",
    });

    expect(generate).toHaveBeenCalledOnce();
    expect(res.data?.[0]?.b64_json).toBe("AAAA");
    trace.end();
  });
});
