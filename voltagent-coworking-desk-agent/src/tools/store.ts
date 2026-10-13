// In-memory desk store, seeded from data/*.json at startup. Tools share this
// one instance so a booking made by one tool is visible to the next.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export type Desk = {
  id: string;
  zone: string;
  kind: string;
  price_eur: number;
  monitor: boolean;
  booked_dates: string[];
};
export type Booking = { booking_id: string; desk_id: string; date: string; member: string };

const load = <T>(file: string): T =>
  JSON.parse(readFileSync(fileURLToPath(new URL(`../../data/${file}`, import.meta.url)), "utf8")) as T;

export const desks = load<Desk[]>("desks.json");
export const amenities = load<Record<string, string[]>>("amenities.json");
export const bookings = load<Booking[]>("bookings.json");

let counter = 3100;
export const nextBookingId = () => `BK-${++counter}`;
