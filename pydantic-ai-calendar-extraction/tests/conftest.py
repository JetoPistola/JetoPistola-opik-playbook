import os

# Agent construction resolves the OpenAI provider and needs a key to exist. The placeholder is
# never used: tests replace the model with a FunctionModel via agent.override.
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-not-used")
