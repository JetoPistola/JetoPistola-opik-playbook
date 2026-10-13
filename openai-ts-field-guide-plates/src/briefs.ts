// The plate brief, kept as a template with {{placeholders}} filled per species.

export const BRIEF = `Illustration of a bird for a regional field guide.
Species: {{common_name}}, found in {{habitat}}.
Show it {{pose_note}}.
Distinctive features: {{field_marks}}.`;

export function render(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) => values[key] ?? "");
}
