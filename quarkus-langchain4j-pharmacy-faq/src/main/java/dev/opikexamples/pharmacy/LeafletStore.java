package dev.opikexamples.pharmacy;

import jakarta.enterprise.context.ApplicationScoped;
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
 * need a vector store.
 */
@ApplicationScoped
public class LeafletStore {

    record Leaflet(String name, String text) {}

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
        Set<String> q = words(question);
        return all().stream()
                .sorted(Comparator.comparingInt((Leaflet l) -> overlap(q, l.text())).reversed())
                .limit(topK).toList();
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
}
