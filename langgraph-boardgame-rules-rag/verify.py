import opik
c = opik.Opik()
P = "langgraph-boardgame-rules-rag"
c.flush()  # make sure everything from the last run has reached Opik before querying
traces = c.search_traces(project_name=P, max_results=1000)
print("traces", len(traces))
for t in traces[:3]:
    print(" ", t.name, "|", str(t.input)[:70])
spans = c.search_spans(project_name=P, max_results=1000)
from collections import Counter
print("spans", len(spans), Counter((s.name, s.type) for s in spans).most_common(10))
print("usage spans", sum(1 for s in spans if s.usage), "cost spans", sum(1 for s in spans if s.total_estimated_cost))
ds = c.get_dataset(P)
print("dataset items", len(ds.get_items()))
exps = c.rest_client.experiments.find_experiments(dataset_id=None, name=None) if False else None
for e in c.rest_client.experiments.find_experiments(dataset_id=c.rest_client.datasets.get_dataset_by_identifier(dataset_name=P).id).content:
    print("experiment", e.name, e.trace_count, [(f.name, round(f.value,3)) for f in (e.feedback_scores or [])])
