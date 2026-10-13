import { Agent } from "@voltagent/core";
import { bookDesk, cancelBooking, checkDeskAvailability, listAmenities } from "../tools/index.ts";

export const deskAgent = new Agent({
  name: "driftwood-desk-assistant",
  model: "openai/gpt-4o-mini",
  instructions:
    "You are the desk-booking assistant for Driftwood Cowork, a small coworking space. " +
    "Never guess availability or amenities: call check_desk_availability and list_amenities. " +
    "Only call book_desk after confirming the desk is free on that date, and only when the member " +
    "clearly asks to book. Always repeat the booking id back. Use cancel_booking only with a booking id. " +
    "Today is 2026-10-30. Be friendly and brief: 2-4 sentences.",
  tools: [checkDeskAvailability, bookDesk, listAmenities, cancelBooking],
});
