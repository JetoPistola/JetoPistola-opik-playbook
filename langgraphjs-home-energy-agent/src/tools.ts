import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const here = dirname(fileURLToPath(import.meta.url));
const home = JSON.parse(readFileSync(resolve(here, "../data/home.json"), "utf8"));

const rateAt = (hour: number): number =>
  home.tariff.bands.find((b: any) => hour >= b.from && hour < b.to).eur_per_kwh;

const schedule: { appliance: string; start_hour: number }[] = [];

export const readMeter = tool(
  async ({ from_hour, to_hour }) => {
    const slice = home.meter_yesterday_kwh_by_hour.slice(from_hour, to_hour);
    const total = slice.reduce((a: number, b: number) => a + b, 0);
    return JSON.stringify({ from_hour, to_hour, kwh_by_hour: slice, total_kwh: +total.toFixed(2) });
  },
  {
    name: "read_meter",
    description: "Read yesterday's smart-meter usage in kWh for the hour range [from_hour, to_hour), hours 0-24.",
    schema: z.object({ from_hour: z.number().int().min(0).max(23), to_hour: z.number().int().min(1).max(24) }),
  },
);

export const listAppliances = tool(
  async () => JSON.stringify(home.appliances),
  { name: "list_appliances", description: "List household appliances with power draw (kW), cycle length (hours) and whether they can be shifted.", schema: z.object({}) },
);

export const estimateCost = tool(
  async ({ appliance_id, start_hour }) => {
    const a = home.appliances.find((x: any) => x.id === appliance_id);
    if (!a) return JSON.stringify({ error: `unknown appliance ${appliance_id}` });
    let cost = 0;
    for (let h = 0; h < Math.ceil(a.cycle_hours); h++) {
      const frac = Math.min(1, a.cycle_hours - h);
      cost += a.kw * frac * rateAt((start_hour + h) % 24);
    }
    return JSON.stringify({ appliance_id, start_hour, cycle_kwh: +(a.kw * a.cycle_hours).toFixed(2), cost_eur: +cost.toFixed(2), tariff: home.tariff.name });
  },
  {
    name: "estimate_cost",
    description: "Estimate the cost in EUR of one full cycle of an appliance if started at start_hour (0-23), using the time-of-use tariff. Bands: night 00-06 0.11, day 06-17 0.26, peak 17-21 0.41, evening 21-24 0.19 EUR/kWh.",
    schema: z.object({ appliance_id: z.string(), start_hour: z.number().int().min(0).max(23) }),
  },
);

export const scheduleAppliance = tool(
  async ({ appliance_id, start_hour }) => {
    const a = home.appliances.find((x: any) => x.id === appliance_id);
    if (!a) return JSON.stringify({ error: `unknown appliance ${appliance_id}` });
    if (!a.flexible) return JSON.stringify({ error: `${a.name} is not schedulable` });
    schedule.push({ appliance: appliance_id, start_hour });
    return JSON.stringify({ confirmed: true, appliance_id, start_hour, ends_hour: (start_hour + Math.ceil(a.cycle_hours)) % 24 });
  },
  {
    name: "schedule_appliance",
    description: "Schedule a flexible appliance to start its cycle at start_hour (0-23) tomorrow.",
    schema: z.object({ appliance_id: z.string(), start_hour: z.number().int().min(0).max(23) }),
  },
);

export const tools = [readMeter, listAppliances, estimateCost, scheduleAppliance];
