"""Fictional messages plus the plain-language assertions that judge them.

Item data holds ONLY the message. Expected values live in the assertions so
the LLM judge cannot read the answer key from the data.
"""

GLOBAL_ASSERTIONS = [
    "Every non-null value in the output is stated in, or directly derivable from, the message",
    "No value is invented: a start time, end time, location or attendee that the message does not mention is null or empty",
    "If date is not null it is formatted YYYY-MM-DD, and times are 24-hour HH:MM",
]

CASES = [
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "Subject: Tidepool sync\nHi all - let's meet Thursday 5 March, 14:00 to 15:30 in "
            "Room Albatross to go over the harbor dashboard. Ines, Kofi and Rhea please come. -Marguerite"
        )},
        "assertions": [
            "The date is 2026-03-05, the start time is 14:00 and the end time is 15:30",
            "The location is Room Albatross and the attendees include Ines, Kofi and Rhea",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "hey! dinner w/ the Okonkwos next friday at 7pm? I'll book somewhere, no idea where yet"
        )},
        "assertions": [
            "The date is 2026-03-13 and the start time is 19:00",
            "The end time is null because no duration or end is mentioned",
            "The location is null because the sender has not chosen a restaurant",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "[voicemail] hi it's Pavel from the dental office, calling to confirm your cleaning, "
            "that's tomorrow morning at nine thirty. Call back if that doesn't work. Bye."
        )},
        "assertions": [
            "The date is 2026-03-03 and the start time is 09:30",
            "The end time and location are null, and attendees are empty or contain only Pavel",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "Reminder: quarterly planning offsite on 2026-03-19. Doors open 09:00, wrap by 17:00 CET. "
            "Venue: Hafenhaus, Kaistrasse 4, Hamburg. Attendees: Dagny Holm, Tobias Wren."
        )},
        "assertions": [
            "The date is 2026-03-19, the start is 09:00, the end is 17:00 and the timezone is CET",
            "The location mentions Hafenhaus in Hamburg and the attendees are Dagny Holm and Tobias Wren",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "Team lunch sometime this week, whenever works - Yusuf"
        )},
        "assertions": [
            "The date, start time, end time and location are all null, because the message fixes none of them",
            "The attendees list is empty or contains only Yusuf; no other people are invented",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "Fwd: invite - Brindle & Co onboarding call, Tue 10 Mar, 10am Pacific, link: "
            "https://meet.example.test/brindle-onb. Bring your laptop. Duration TBD."
        )},
        "assertions": [
            "The date is 2026-03-10, the start time is 10:00 and the timezone is Pacific (PT/PST)",
            "The end time is null because the duration is explicitly TBD",
            "The location is the link https://meet.example.test/brindle-onb",
        ],
    },
    {
        "data": {"message": (
            "Sent: Monday 2026-03-02\n"
            "Book club moved! Now Wed the 11th, 6:30pm at Odile's place. Same crowd as always."
        )},
        "assertions": [
            "The date is 2026-03-11 and the start time is 18:30 and the location is Odile's place",
            "The attendees are empty, because 'same crowd as always' names nobody",
            "The end time is null",
        ],
    },
]
