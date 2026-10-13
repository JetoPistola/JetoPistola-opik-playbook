package dev.opikexamples.pharmacy;

import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Scope;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Tiny keyword retriever over the markdown leaflets in docs/. Four short files do not
 * need a vector store; what matters here is that retrieval gets its own span, with the
 * question as input and the chosen leaflets as output.
 */
@ApplicationScoped
public class LeafletStore {

    record Leaflet(String name, String text) {}

    // OpenTelemetry tracer (from quarkus-opentelemetry): spans made with it are exported to Opik over OTLP.
    @Inject
    Tracer tracer;

    @ConfigProperty(name = "pharmacy.docs-dir", defaultValue = "docs")
    String docsDir;

    private List<Leaflet> leaflets;

    private synchronized List<Leaflet> all() {
        if (leaflets == null) {
            try (Stream<Path> files = Files.list(Path.of(docsDir))) {
                leaflets = files.filter(p -> p.toString().endsWith(".md")).sorted()
                        .map(p -> new Leaflet(p.getFileName().toString(), read(p)))
                        .toList();
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        }
        return leaflets;
    }

    private static String read(Path p) {
        try {
            return Files.readString(p);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** Returns the {@code topK} leaflets sharing the most words with the question. */
    public List<Leaflet> retrieve(String question, int topK) {
        // Manual span: shows up in Opik as a child of "GET /ask" named retrieve_leaflets. Without it
        // retrieval is invisible and you cannot tell which leaflets the prompt was built from.
        Span span = tracer.spanBuilder("retrieve_leaflets").startSpan();
        try (Scope ignored = span.makeCurrent()) {
            // "input" / "output" are the attribute names Opik reads for a span's Input / Output panes.
            span.setAttribute("input", "{\"question\":" + json(question) + ",\"top_k\":" + topK + "}");
            Set<String> q = words(question);
            List<Leaflet> hits = all().stream()
                    .sorted(Comparator.comparingInt((Leaflet l) -> overlap(q, l.text())).reversed())
                    .limit(topK).toList();
            span.setAttribute("output", "{\"leaflets\":["
                    + hits.stream().map(l -> json(l.name())).collect(Collectors.joining(",")) + "]}");
            return hits;
        } finally {
            span.end(); // an unended span is never exported, so it would never reach Opik
        }
    }

    private static int overlap(Set<String> q, String text) {
        Set<String> t = words(text);
        t.retainAll(q);
        return t.size();
    }

    private static Set<String> words(String s) {
        return Arrays.stream(s.toLowerCase(Locale.ROOT).split("[^a-z0-9]+"))
                .filter(w -> w.length() > 3).collect(Collectors.toCollection(HashSet::new));
    }

    static String json(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\"";
    }
}
