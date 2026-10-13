// Two versions of the plate brief, kept as Mustache templates and registered in
// the Opik prompt library (see ensureVersion in main.ts) as v1 and v2.
// v1 describes the bird; v2 adds the house conventions of a printed field guide.

export const PROMPT_NAME = "field-guide-plate-brief";

export const BRIEF_V1 = `Illustration of a bird for a regional field guide.
Species: {{common_name}}, found in {{habitat}}.
Show it {{pose_note}}.
Distinctive features: {{field_marks}}.`;

export const BRIEF_V2 = `Illustration plate for a regional field guide.
Species: {{common_name}}, found in {{habitat}}.
Show it {{pose_note}}.
Distinctive features: {{field_marks}}.

Plate conventions:
- Plain neutral cream background, no scenery.
- Strict side profile, whole bird visible, centered.
- Gouache painting style, natural proportions.
- Draw a thin leader line from each field mark to a short printed label.`;

export const V1_CHANGE = "Initial brief: species, habitat, pose, field marks";
export const V2_CHANGE =
  "Add plate conventions: neutral background, side profile, labeled field marks";
