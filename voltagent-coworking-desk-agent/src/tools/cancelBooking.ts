import { createTool } from "@voltagent/core";
import { z } from "zod";
import { bookings, desks } from "./store.ts";

export const cancelBooking = createTool({
  name: "cancel_booking",
  description: "Cancel a booking by its id (BK-xxxx) and free the desk.",
  parameters: z.object({ booking_id: z.string() }),
  execute: async ({ booking_id }) => {
    const i = bookings.findIndex((b) => b.booking_id === booking_id);
    if (i < 0) return { ok: false, error: `no booking ${booking_id}` };
    const [b] = bookings.splice(i, 1);
    const desk = desks.find((d) => d.id === b.desk_id);
    if (desk) desk.booked_dates = desk.booked_dates.filter((x) => x !== b.date);
    return { ok: true, cancelled: b };
  },
});
