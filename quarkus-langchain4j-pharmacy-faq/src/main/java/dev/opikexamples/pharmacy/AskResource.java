package dev.opikexamples.pharmacy;

import io.opentelemetry.api.trace.Span;
import jakarta.inject.Inject;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;

import java.util.List;
import java.util.stream.Collectors;

@Path("/ask")
public class AskResource {

    @Inject
    LeafletStore store;

    @Inject
    PharmacyBot bot;

    @GET
    @Produces(MediaType.TEXT_PLAIN)
    public String ask(@QueryParam("q") String q) {
        // Quarkus already opened the server span (it becomes the trace root, "GET /ask"). The
        // "input" and "output" attributes below fill the trace Input/Output columns in Opik.
        Span root = Span.current();
        root.setAttribute("input", LeafletStore.json(q));

        List<LeafletStore.Leaflet> hits = store.retrieve(q, 2);
        String context = hits.stream().map(LeafletStore.Leaflet::text).collect(Collectors.joining("\n---\n"));
        String answer = bot.answer(context, q);

        root.setAttribute("output", LeafletStore.json(answer));
        return answer;
    }
}
