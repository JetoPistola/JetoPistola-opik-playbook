package dev.opikexamples.pharmacy;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;
import io.quarkiverse.langchain4j.RegisterAiService;

// quarkus-langchain4j + quarkus-opentelemetry trace this interface automatically: an AI-service span
// plus a "completion <model>" llm span (gen_ai.* attributes -> usage and cost in Opik). No code needed.
@RegisterAiService
public interface PharmacyBot {

    @SystemMessage("""
            You are the FAQ assistant of Larkspur Community Pharmacy. Answer ONLY from the leaflets below,
            in at most three short sentences, and mention the leaflet id (like L-02) you used.
            You are not a clinician: for anything about a person's own treatment, dosing changes,
            symptoms, interactions or what is safe for them, do not advise. Tell them to ask the
            pharmacist at the consultation desk. If the leaflets do not cover the question, say so.

            LEAFLETS:
            {leaflets}
            """)
    @UserMessage("{question}")
    String answer(@V("leaflets") String leaflets, @V("question") String question);
}
