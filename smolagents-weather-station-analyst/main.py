"""Weather-station analyst: a smolagents CodeAgent that writes pandas code to answer questions about a CSV."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT = "smolagents-weather-station-analyst"
CSV = Path(__file__).parent / "data" / "readings.csv"

for p in Path(__file__).resolve().parents:  # walk up to a repo-root .env
    if (p / ".env").exists():
        load_dotenv(p / ".env")
        break
os.environ.pop("OPENAI_BASE_URL", None)

from smolagents import CodeAgent, OpenAIServerModel  # noqa: E402

agent = CodeAgent(
    tools=[],
    model=OpenAIServerModel(model_id="gpt-4o-mini"),
    additional_authorized_imports=["pandas"],
    max_steps=6,
)

BRIEFING = f"""You analyse readings from the Larkspur Hill community weather station.
Hourly data, 2-15 March 2026, is in the CSV at: {CSV}
Columns: timestamp (YYYY-MM-DD HH:MM), temp_c, humidity_pct, wind_kmh, rain_mm (rain in that hour).
Load it with pandas, inspect it, and answer with concrete numbers. If something in the data
looks wrong or untrustworthy, say so plainly in your answer. Reply in two or three sentences."""

QUESTIONS = [
    "How much rain fell in total over the fortnight, and which day was the wettest?",
    "What was the average wind speed per day, and which day was the calmest?",
    "What were the hottest and coldest readings of the fortnight, and when did they happen?",
]


def main() -> None:
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n=== Question {i}: {q}")
        print(f"Answer {i}:", agent.run(BRIEFING + "\n\nQuestion: " + q))


if __name__ == "__main__":
    main()
