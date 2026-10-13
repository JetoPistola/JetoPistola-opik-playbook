import Mustache from "mustache";

// Opik's Prompt.format renders Mustache templates with HTML escaping off;
// this does the same, so tests exercise the real templates offline.
export const renderBrief = (template: string, vars: Record<string, unknown>): string =>
  Mustache.render(template, vars, {}, { escape: (t: string) => t });
