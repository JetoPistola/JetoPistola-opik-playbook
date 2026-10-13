import { createTool } from "@voltagent/core";
import { z } from "zod";
import { desks } from "./store.ts";

export const checkDeskAvailability = createTool({
  name: "check_desk_availability",
  description: "List desks that are still free on a date (YYYY-MM-DD), optionally filtered by zone or monitor.",
  parameters: z.object({
    date: z.string().describe("ISO date, e.g. 2026-11-03"),
    zone: z.string().optional().describe("Harbor Loft, Quiet Room or Standing Bar"),
    needs_monitor: z.boolean().optional(),
  }),
  execute: async ({ date, zone, needs_monitor }) => {
    const free = desks
      .filter((d) => !d.booked_dates.includes(date))
      .filter((d) => !zone || d.zone.toLowerCase() === zone.toLowerCase())
      .filter((d) => !needs_monitor || d.monitor)
      .map(({ id, zone, kind, price_eur, monitor }) => ({ id, zone, kind, price_eur, monitor }));
    return { date, free_desks: free };
  },
});
