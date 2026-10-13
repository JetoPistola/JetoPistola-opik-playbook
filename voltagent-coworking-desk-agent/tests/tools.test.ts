import { beforeEach, describe, expect, it, vi } from "vitest";

// The tools share one in-memory store seeded from data/*.json, so load a fresh copy per test.
// Tools only need their arguments; the second execute() argument (VoltAgent's options) is unused.
type Exec = (args: Record<string, unknown>) => Promise<any>;
let run: (name: string, args: Record<string, unknown>) => Promise<any>;

beforeEach(async () => {
  vi.resetModules();
  const tools = await import("../src/tools/index.ts");
  const byName: Record<string, { execute?: unknown }> = {
    check_desk_availability: tools.checkDeskAvailability,
    book_desk: tools.bookDesk,
    list_amenities: tools.listAmenities,
    cancel_booking: tools.cancelBooking,
  };
  run = (name, args) => (byName[name].execute as Exec)(args);
});

describe("check_desk_availability", () => {
  it("excludes desks booked on the date and honours zone and monitor filters", async () => {
    const r = await run("check_desk_availability", { date: "2026-11-03", zone: "harbor loft", needs_monitor: true });
    expect(r.free_desks.map((d: { id: string }) => d.id)).toEqual(["HD-02"]);
  });

  it("returns every desk on a date nobody booked", async () => {
    const r = await run("check_desk_availability", { date: "2027-01-01" });
    expect(r.free_desks.length).toBeGreaterThanOrEqual(5);
  });
});

describe("book_desk", () => {
  it("books a free desk, issues the next id and blocks a double booking", async () => {
    const ok = await run("book_desk", { desk_id: "HD-02", date: "2026-11-03", member: "Priya Natarajan" });
    expect(ok).toMatchObject({ ok: true, booking_id: "BK-3101", zone: "Harbor Loft", price_eur: 18 });
    const again = await run("book_desk", { desk_id: "HD-02", date: "2026-11-03", member: "Someone" });
    expect(again).toEqual({ ok: false, error: "HD-02 is already booked on 2026-11-03" });
  });

  it("rejects an unknown desk", async () => {
    expect(await run("book_desk", { desk_id: "ZZ-99", date: "2026-11-03", member: "A" })).toEqual({
      ok: false,
      error: "unknown desk ZZ-99",
    });
  });
});

describe("list_amenities", () => {
  it("returns one zone case-insensitively, all zones when omitted, and an error for unknown zones", async () => {
    expect(await run("list_amenities", { zone: "quiet room" })).toEqual({
      "Quiet Room": ["fast wifi", "no calls policy", "lockers", "free filter coffee"],
    });
    expect(Object.keys(await run("list_amenities", {}))).toEqual(["Harbor Loft", "Quiet Room", "Standing Bar"]);
    const bad = await run("list_amenities", { zone: "Rooftop" });
    expect(bad.error).toBe("unknown zone Rooftop");
  });
});

describe("cancel_booking", () => {
  it("cancels a seeded booking and frees the desk for that date", async () => {
    const r = await run("cancel_booking", { booking_id: "BK-3002" });
    expect(r).toMatchObject({ ok: true, cancelled: { desk_id: "QR-07", date: "2026-11-03" } });
    const free = await run("check_desk_availability", { date: "2026-11-03", zone: "Quiet Room" });
    expect(free.free_desks.map((d: { id: string }) => d.id)).toContain("QR-07");
  });

  it("reports an unknown booking id", async () => {
    expect(await run("cancel_booking", { booking_id: "BK-0000" })).toEqual({ ok: false, error: "no booking BK-0000" });
  });
});
