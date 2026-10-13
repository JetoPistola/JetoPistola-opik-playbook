import { describe, expect, it } from "vitest";
import { estimateCost, listAppliances, readMeter, scheduleAppliance, tools } from "../src/tools.js";

describe("energy tools against data/home.json", () => {
  it("exposes the four tools by name", () => {
    expect(tools.map((t) => t.name)).toEqual(["read_meter", "list_appliances", "estimate_cost", "schedule_appliance"]);
  });

  it("read_meter sums the peak window 17-21 to 11.5 kWh", async () => {
    const out = JSON.parse(await readMeter.invoke({ from_hour: 17, to_hour: 21 }));
    expect(out.kwh_by_hour).toEqual([2.8, 3.4, 3.1, 2.2]);
    expect(out.total_kwh).toBe(11.5);
  });

  it("list_appliances returns all four with the heat pump not flexible", async () => {
    const out = JSON.parse(await listAppliances.invoke({}));
    expect(out.map((a: any) => a.id)).toEqual(["dishwasher", "dryer", "ev_charger", "heat_pump"]);
    expect(out.find((a: any) => a.id === "heat_pump").flexible).toBe(false);
  });

  it("estimate_cost prices the dishwasher higher at 18:00 than at 02:00", async () => {
    const peak = JSON.parse(await estimateCost.invoke({ appliance_id: "dishwasher", start_hour: 18 }));
    const night = JSON.parse(await estimateCost.invoke({ appliance_id: "dishwasher", start_hour: 2 }));
    expect(peak.cost_eur).toBe(1.15); // 1.4 kW * 2 h * 0.41
    expect(night.cost_eur).toBe(0.31); // 1.4 kW * 2 h * 0.11
    expect(night.cycle_kwh).toBe(2.8);
  });

  it("estimate_cost wraps past midnight and reports unknown appliances", async () => {
    const wrap = JSON.parse(await estimateCost.invoke({ appliance_id: "dishwasher", start_hour: 23 }));
    expect(wrap.cost_eur).toBe(0.42); // 1.4 * 0.19 (23h) + 1.4 * 0.11 (00h)
    const bad = JSON.parse(await estimateCost.invoke({ appliance_id: "toaster", start_hour: 1 }));
    expect(bad.error).toMatch(/unknown appliance/);
  });

  it("schedule_appliance confirms flexible appliances and rejects the heat pump", async () => {
    const ok = JSON.parse(await scheduleAppliance.invoke({ appliance_id: "dishwasher", start_hour: 2 }));
    expect(ok).toEqual({ confirmed: true, appliance_id: "dishwasher", start_hour: 2, ends_hour: 4 });
    const no = JSON.parse(await scheduleAppliance.invoke({ appliance_id: "heat_pump", start_hour: 2 }));
    expect(no.error).toMatch(/not schedulable/);
  });
});
