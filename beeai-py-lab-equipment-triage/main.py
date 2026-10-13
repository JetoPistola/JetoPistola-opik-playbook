import asyncio
import time

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))  # walks up to the repo-root .env

from tracing import setup_tracing  # noqa: E402

# Registers the OTLP exporter and BeeAI instrumentor, so each agent.run() becomes one Opik trace.
provider = setup_tracing()  # instrument BEFORE building agents

from beeai_framework.agents.react import ReActAgent  # noqa: E402
from beeai_framework.backend import ChatModel  # noqa: E402
from beeai_framework.memory import UnconstrainedMemory  # noqa: E402

from tools import check_calibration_schedule, find_service_contact, lookup_instrument_log  # noqa: E402

INSTRUCTIONS = """You triage problem reports for instruments in a university research lab. Today is 2026-10-13.
For every report: identify the instrument, call lookup_instrument_log for its history, call
check_calibration_schedule if calibration could matter, and call find_service_contact for who to call.
Never state a contact or date you did not get from a tool.
Finish with exactly three lines:
SEVERITY: one of critical / high / routine
NEXT ACTION: one sentence, what the researcher should do right now
CONTACT: name, phone, and expected response time"""

REPORTS = [
    "The -80 freezer in Cold Room B (FZ-80-B) is reading -71C this morning, someone left the door open last night. It holds our cell lines.",
    "The big floor centrifuge CF-02 shook violently at 4200 rpm and the imbalance sensor stopped it again. Is it OK to keep using?",
    "Spectrophotometer SP-07 readings in the 260 nm range look a bit noisy today. Not urgent, I just wanted to flag it.",
]


async def main() -> None:
    start = time.time()
    for i, report in enumerate(REPORTS, 1):
        agent = ReActAgent(
            llm=ChatModel.from_name("openai:gpt-4o-mini"),
            tools=[lookup_instrument_log, check_calibration_schedule, find_service_contact],
            memory=UnconstrainedMemory(),
        )
        result = await agent.run(
            f"{INSTRUCTIONS}\n\nReport: {report}",
            execution={"max_iterations": 6, "max_retries_per_step": 1, "total_max_retries": 2},
        )
        print(f"\n=== Report {i}: {report}\n{result.last_message.text}")
    # Flush + shutdown drain the batch processor; without them the last trace can be lost at exit.
    provider.force_flush()
    provider.shutdown()
    print(f"\nDone in {time.time() - start:.0f}s. Open project 'beeai-py-lab-equipment-triage' in Opik.")


asyncio.run(main())
