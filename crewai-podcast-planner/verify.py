"""Print what Opik recorded for the project (run after the planner): one trace per kickoff, then
tokens and dollar cost for each agent's llm span."""
import opik

c = opik.Opik()
# One trace per kickoff is the claim to check, so count the project's traces first.
traces = c.search_traces(project_name="crewai-podcast-planner")
print("traces:", len(traces))
for t in traces:
    spans = c.search_spans(project_name="crewai-podcast-planner", trace_id=t.id)
    # Each agent's model call is an llm span; usage and cost live on these spans.
    llm = [s for s in spans if s.type == "llm"]
    print(t.id, t.name, "spans:", len(spans), "llm spans:", len(llm), "trace usage:", t.usage, "cost:", t.total_estimated_cost)
    for s in llm:
        # total_estimated_cost is a top-level span field (not inside usage); it must be non-null.
        print("  ", s.name, s.model, s.usage, s.total_estimated_cost)
