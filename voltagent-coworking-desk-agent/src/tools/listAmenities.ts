import { createTool } from "@voltagent/core";
import { z } from "zod";
import { amenities } from "./store.ts";

export const listAmenities = createTool({
  name: "list_amenities",
  description: "List what a zone offers (wifi, coffee, booths, lockers...). Omit zone for all zones.",
  parameters: z.object({ zone: z.string().optional() }),
  execute: async ({ zone }) => {
    if (!zone) return amenities;
    const key = Object.keys(amenities).find((k) => k.toLowerCase() === zone.toLowerCase());
    return key ? { [key]: amenities[key] } : { error: `unknown zone ${zone}`, zones: Object.keys(amenities) };
  },
});
