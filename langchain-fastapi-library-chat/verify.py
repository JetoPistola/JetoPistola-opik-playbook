"""Query Opik and print what the demo run produced."""
import opik

from library_chat.server import PROJECT_NAME

c = opik.Opik()
traces = c.search_traces(project_name=PROJECT_NAME, max_results=200)
print("traces:", len(traces))
cost = sum((t.total_estimated_cost or 0) for t in traces)
print("total_estimated_cost: %.5f" % cost)
t = traces[0]
print("sample root input/output types:", type(t.input).__name__, type(t.output).__name__)
print("sample input:", t.input, "\nsample output:", t.output)
spans = c.search_spans(project_name=PROJECT_NAME, trace_id=t.id)
print("sample span tree:", sorted((s.type, s.name) for s in spans))
threads = c.search_threads(project_name=PROJECT_NAME)
print("threads:", len(threads))
for th in sorted(threads, key=lambda x: x.id):
    print(" ", th.id, "turns:", th.number_of_messages)
by_id = {s.id: s for s in spans}
for s in spans:
    p = by_id.get(s.parent_span_id)
    print(f"  span {s.name} ({s.type}) parent={p.name if p else 'root'}")
