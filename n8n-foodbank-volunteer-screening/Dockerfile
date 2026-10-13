# n8n with Opik's OpenTelemetry hooks installed.
# n8n-observability registers lifecycle hooks (EXTERNAL_HOOK_FILES) that emit
# one span per workflow execution and one per node; docker-compose.yml points
# the OTLP exporter at Opik.
FROM n8nio/n8n:2.41.7

USER root
# n8n-observability supplies the hooks that turn each execution and node into an
# OpenTelemetry span; without it nothing reaches Opik.
RUN npm install -g n8n-observability@1.0.3
# n8n loads this hook file at startup, so no tracing node is needed in the workflow.
ENV EXTERNAL_HOOK_FILES=/usr/local/lib/node_modules/n8n-observability/dist/hooks.cjs
USER node
