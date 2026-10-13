package dev.opikexamples.pharmacy;

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
        List<LeafletStore.Leaflet> hits = store.retrieve(q, 2);
        String context = hits.stream().map(LeafletStore.Leaflet::text).collect(Collectors.joining("\n---\n"));
        return bot.answer(context, q);
    }
}
