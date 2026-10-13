// Six fictional nutrition-facts labels, drawn as SVG and rasterised to PNG at
// run time with resvg (pure JS/WASM-free native binding, no network). Each
// label carries the ground truth the test suite pins down.
import { Resvg } from "@resvg/resvg-js";

export interface Truth {
  product_name: string;
  serving_size: string;
  calories: number | null;
  total_fat_g: number | null;
  sodium_mg: number | null;
  total_carbs_g: number | null;
  protein_g: number | null;
  allergens: string[];
}

export interface Label {
  id: string;
  challenge: string;
  truth: Truth;
  svg: string;
}

interface Row {
  name: string;
  values: string[];
  bold?: boolean;
}

interface Style {
  width?: number;
  height?: number;
  font?: number; // base font size
  rotate?: number;
  blur?: number;
  headers?: string[]; // column headers over the value columns
  footer?: string[];
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

function draw(title: string, serving: string, rows: Row[], st: Style = {}): string {
  const w = st.width ?? 420;
  const f = st.font ?? 20;
  const lh = f * 1.9;
  const cols = st.headers ?? ["Amount"];
  const colX = cols.map((_, i) => w - 40 - (cols.length - 1 - i) * 130);
  let y = 40 + f * 1.6;
  const out: string[] = [];
  out.push(`<text x="30" y="${y}" font-size="${f * 1.4}" font-weight="bold">${esc(title)}</text>`);
  y += lh;
  out.push(`<text x="30" y="${y}" font-size="${f * 0.9}">${esc(serving)}</text>`);
  y += lh * 0.5;
  out.push(`<rect x="30" y="${y}" width="${w - 60}" height="8"/>`);
  y += lh * 0.8;
  cols.forEach((c, i) =>
    out.push(`<text x="${colX[i]}" y="${y}" font-size="${f * 0.85}" font-weight="bold" text-anchor="end">${esc(c)}</text>`),
  );
  y += lh * 0.4;
  for (const r of rows) {
    out.push(`<line x1="30" x2="${w - 30}" y1="${y}" y2="${y}" stroke="#000" stroke-width="1.5"/>`);
    y += lh * 0.85;
    out.push(`<text x="30" y="${y}" font-size="${f}" font-weight="${r.bold ? "bold" : "normal"}">${esc(r.name)}</text>`);
    r.values.forEach((v, i) =>
      out.push(`<text x="${colX[i]}" y="${y}" font-size="${f}" text-anchor="end">${esc(v)}</text>`),
    );
    y += lh * 0.25;
  }
  out.push(`<rect x="30" y="${y}" width="${w - 60}" height="5"/>`);
  y += lh * 0.8;
  for (const line of st.footer ?? []) {
    out.push(`<text x="30" y="${y}" font-size="${f * 0.8}">${esc(line)}</text>`);
    y += f * 1.2;
  }
  const h = st.height ?? Math.ceil(y + 30);
  const filter = st.blur
    ? `<defs><filter id="b"><feGaussianBlur stdDeviation="${st.blur}"/></filter></defs>`
    : "";
  const g = `transform="rotate(${st.rotate ?? 0} ${w / 2} ${h / 2})"${st.blur ? ' filter="url(#b)"' : ""}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" font-family="Helvetica, Arial, sans-serif">
${filter}<rect width="100%" height="100%" fill="#fff"/><g ${g}><rect x="14" y="14" width="${w - 28}" height="${h - 28}" fill="none" stroke="#000" stroke-width="3"/>
${out.join("\n")}</g></svg>`;
}

export const LABELS: Label[] = [
  {
    id: "oat-honey-bar",
    challenge: "clean, high-contrast baseline",
    truth: {
      product_name: "Oat & Honey Crunch Bar",
      serving_size: "1 bar (40 g)",
      calories: 170,
      total_fat_g: 6,
      sodium_mg: 95,
      total_carbs_g: 26,
      protein_g: 3,
      allergens: ["oats", "tree nuts"],
    },
    svg: draw(
      "Nutrition Facts",
      "Oat & Honey Crunch Bar - Serving size 1 bar (40 g)",
      [
        { name: "Calories", values: ["170"], bold: true },
        { name: "Total Fat", values: ["6 g"] },
        { name: "Sodium", values: ["95 mg"] },
        { name: "Total Carbohydrate", values: ["26 g"] },
        { name: "Protein", values: ["3 g"] },
      ],
      { footer: ["Contains: oats, tree nuts."] },
    ),
  },
  {
    id: "per-100g-trap",
    challenge: "two columns: per 100 g and per serving; the answer is per serving",
    truth: {
      product_name: "Smoked Paprika Chickpea Crisps",
      serving_size: "30 g",
      calories: 140,
      total_fat_g: 5,
      sodium_mg: 210,
      total_carbs_g: 18,
      protein_g: 5,
      allergens: [],
    },
    svg: draw(
      "Nutrition Facts",
      "Smoked Paprika Chickpea Crisps - Serving size 30 g",
      [
        { name: "Calories", values: ["467", "140"], bold: true },
        { name: "Total Fat", values: ["16.7 g", "5 g"] },
        { name: "Sodium", values: ["700 mg", "210 mg"] },
        { name: "Total Carbohydrate", values: ["60 g", "18 g"] },
        { name: "Protein", values: ["16.7 g", "5 g"] },
      ],
      { width: 500, headers: ["Per 100 g", "Per serving"], footer: ["Allergens: none declared."] },
    ),
  },
  {
    id: "tiny-print",
    challenge: "very small type on a big canvas",
    truth: {
      product_name: "Lemon Poppy Seed Loaf",
      serving_size: "1 slice (55 g)",
      calories: 210,
      total_fat_g: 9,
      sodium_mg: 180,
      total_carbs_g: 30,
      protein_g: 4,
      allergens: ["wheat", "eggs", "milk"],
    },
    svg: draw(
      "Nutrition Facts",
      "Lemon Poppy Seed Loaf - Serving size 1 slice (55 g)",
      [
        { name: "Calories", values: ["210"], bold: true },
        { name: "Total Fat", values: ["9 g"] },
        { name: "Sodium", values: ["180 mg"] },
        { name: "Total Carbohydrate", values: ["30 g"] },
        { name: "Protein", values: ["4 g"] },
      ],
      { width: 900, font: 9, footer: ["Contains: wheat, eggs, milk."] },
    ),
  },
  {
    id: "rotated-blurry",
    challenge: "rotated about 4 degrees and blurred, as if photographed in a hurry",
    truth: {
      product_name: "Cocoa Almond Granola",
      serving_size: "1/2 cup (55 g)",
      calories: 260,
      total_fat_g: 12,
      sodium_mg: 85,
      total_carbs_g: 33,
      protein_g: 7,
      allergens: ["almonds", "oats"],
    },
    svg: draw(
      "Nutrition Facts",
      "Cocoa Almond Granola - Serving size 1/2 cup (55 g)",
      [
        { name: "Calories", values: ["260"], bold: true },
        { name: "Total Fat", values: ["12 g"] },
        { name: "Sodium", values: ["85 mg"] },
        { name: "Total Carbohydrate", values: ["33 g"] },
        { name: "Protein", values: ["7 g"] },
      ],
      { rotate: 4, blur: 1.2, width: 540, height: 460, footer: ["Contains: almonds, oats."] },
    ),
  },
  {
    id: "no-sodium-line",
    challenge: "the sodium line was never printed; the right answer is null",
    truth: {
      product_name: "Mango Chili Fruit Leather",
      serving_size: "1 strip (20 g)",
      calories: 70,
      total_fat_g: 0,
      sodium_mg: null,
      total_carbs_g: 17,
      protein_g: 0,
      allergens: [],
    },
    svg: draw(
      "Nutrition Facts",
      "Mango Chili Fruit Leather - Serving size 1 strip (20 g)",
      [
        { name: "Calories", values: ["70"], bold: true },
        { name: "Total Fat", values: ["0 g"] },
        { name: "Total Carbohydrate", values: ["17 g"] },
        { name: "Protein", values: ["0 g"] },
      ],
      { footer: ["No allergens."] },
    ),
  },
  {
    id: "long-allergens",
    challenge: "a dense allergen paragraph with a may-contain clause",
    truth: {
      product_name: "Sesame Noodle Cup",
      serving_size: "1 cup (85 g)",
      calories: 330,
      total_fat_g: 11,
      sodium_mg: 1040,
      total_carbs_g: 49,
      protein_g: 9,
      allergens: ["wheat", "soy", "sesame"],
    },
    svg: draw(
      "Nutrition Facts",
      "Sesame Noodle Cup - Serving size 1 cup (85 g)",
      [
        { name: "Calories", values: ["330"], bold: true },
        { name: "Total Fat", values: ["11 g"] },
        { name: "Sodium", values: ["1040 mg"] },
        { name: "Total Carbohydrate", values: ["49 g"] },
        { name: "Protein", values: ["9 g"] },
      ],
      {
        width: 520,
        footer: [
          "Contains: wheat, soy, sesame.",
          "May contain traces of peanuts. Made on shared equipment.",
        ],
      },
    ),
  },
];

export function renderPng(label: Label): Buffer {
  const resvg = new Resvg(label.svg, {
    fitTo: { mode: "zoom", value: 2 },
    font: { loadSystemFonts: true },
  });
  return resvg.render().asPng();
}
