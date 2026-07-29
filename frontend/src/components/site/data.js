export const MODULES = [
  {
    id: "proxy",
    name: "Proxy Classification",
    desc: "Auto-detects and reclassifies invalid IfcBuildingElementProxy entities into correct semantic types.",
    span: "lg:col-span-5 lg:row-span-2",
  },
  {
    id: "pset",
    name: "Pset Analysis",
    desc: "Validates required property sets against IFC schema and project templates.",
    span: "lg:col-span-4",
  },
  {
    id: "storey",
    name: "Storey Quality",
    desc: "Checks storey assignment, elevation logic and vertical containment.",
    span: "lg:col-span-3",
  },
  {
    id: "nbc",
    name: "NBC Compliance",
    desc: "Rule engine mapped to India's National Building Code 2016 — egress, fire, accessibility.",
    span: "lg:col-span-4",
  },
  {
    id: "score",
    name: "Model Quality Score",
    desc: "A single, auditable 0–100 index of overall model health.",
    span: "lg:col-span-3",
  },
  {
    id: "rule",
    name: "Rule Validation",
    desc: "Run custom firm-level and regulatory rulesets against every element.",
    span: "lg:col-span-4",
  },
  {
    id: "heatmap",
    name: "Issue Heatmap",
    desc: "Spatial density map pinpointing where defects cluster in the model.",
    span: "lg:col-span-5",
  },
  {
    id: "geometry",
    name: "Geometry Integrity",
    desc: "Detects overlaps, gaps, self-intersections and degenerate solids.",
    span: "lg:col-span-4",
  },
  {
    id: "version",
    name: "Version Comparison",
    desc: "Diff two IFC revisions and track how quality evolves per submission.",
    span: "lg:col-span-3",
  },
  {
    id: "correction",
    name: "Correction Suggestions",
    desc: "Actionable, element-level fix recommendations ranked by impact.",
    span: "lg:col-span-4",
  },
  {
    id: "bcf",
    name: "BCF Export",
    desc: "Export findings as BuildingSMART BCF for round-trip in Revit / Tekla / ArchiCAD.",
    span: "lg:col-span-5",
  },
  {
    id: "nlq",
    name: "NLQ Assistant",
    desc: "Ask questions about your model in plain English and get grounded answers.",
    span: "lg:col-span-3",
  },
];

export const STEPS = [
  {
    n: "01",
    title: "Upload IFC Model",
    desc: "Drop your IFC2x3 or IFC4 export. No plugins, no manual prep — ArchiShield ingests the raw model.",
  },
  {
    n: "02",
    title: "AI Analysis",
    desc: "Twelve intelligence modules run in parallel against every element, property and relationship.",
  },
  {
    n: "03",
    title: "Quality Score & Report",
    desc: "Receive an auditable Model Quality Score and a clause-by-clause NBC 2016 compliance report.",
  },
  {
    n: "04",
    title: "Ask in Plain English",
    desc: "Interrogate results with the NLQ Assistant — “Which walls fail fire rating on level 3?”",
  },
  {
    n: "05",
    title: "Export Fixes",
    desc: "Push prioritised corrections back to your authoring tool as BCF. Fix once, at the source.",
  },
];

export const DEFECTS = [
  { id: "proxy", label: "Invalid Proxy Elements", top: "18%", side: "left" },
  { id: "pset", label: "Missing Property Sets", top: "40%", side: "right" },
  { id: "geo", label: "Geometry Errors", top: "62%", side: "left" },
  { id: "nbc", label: "NBC Non-Compliant", top: "82%", side: "right" },
];

export const MARQUEE = [
  "IFC4 COMPLIANT",
  "NBC 2016 VALIDATED",
  "BUILDINGSMART BCF",
  "MODEL QUALITY SCORE",
  "PSET INTEGRITY",
  "GEOMETRY VALIDATION",
  "ZERO ON-SITE REWORK",
  "IFC2x3 SUPPORTED",
];
