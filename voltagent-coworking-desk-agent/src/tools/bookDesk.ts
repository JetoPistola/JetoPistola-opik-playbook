import { createTool } from "@voltagent/core";
import { z } from "zod";
import { bookings, desks, nextBookingId } from "./store.ts";

export const bookDesk = createTool({
  name: "book_desk",
  description: "Book a specific desk for a member on a date. Fails if the desk is already taken.",
  parameters: z.object({
    desk_id: z.string(),
    date: z.string().describe("ISO date"),
    member: z.string().describe("Member's full name"),
  }),
  execute: async ({ desk_id, date, member }) => {
    const desk = desks.find((d) => d.id === desk_id);
    if (!desk) return { ok: false, error: `unknown desk ${desk_id}` };
    if (desk.booked_dates.includes(date)) return { ok: false, error: `${desk_id} is already booked on ${date}` };
    desk.booked_dates.push(date);
    const booking = { booking_id: nextBookingId(), desk_id, date, member };
    bookings.push(booking);
    return { ok: true, ...booking, zone: desk.zone, price_eur: desk.price_eur };
  },
});
