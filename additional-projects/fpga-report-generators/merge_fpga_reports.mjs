import fs from "node:fs";

const basePath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/work/fpga_space_report_base_artifact.json";
const recipesPath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_uses_implementation_artifact.json";
const outputPath =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_report_artifact.json";

const base = JSON.parse(fs.readFileSync(basePath, "utf8"));
const recipes = JSON.parse(fs.readFileSync(recipesPath, "utf8"));
const combined = structuredClone(base);

function uniqueById(items) {
  const found = new Map();
  for (const item of items ?? []) {
    if (item?.id && !found.has(item.id)) found.set(item.id, structuredClone(item));
  }
  return [...found.values()];
}

const detailBlocks = recipes.manifest.blocks
  .filter((block) => !["title", "technical_summary"].includes(block.id))
  .map((block) => ({ ...structuredClone(block), id: `space_impl_${block.id}` }));

const insertionIndex = combined.manifest.blocks.findIndex(
  (block) => block.id === "why_space",
);
if (insertionIndex < 0) {
  throw new Error("The base report is missing the why_space insertion point.");
}

combined.manifest.blocks.splice(insertionIndex + 1, 0, ...detailBlocks);

const summary = combined.manifest.blocks.find(
  (block) => block.id === "technical_summary",
);
summary.body +=
  "\n\n**This revised edition also explains exactly how the 30 principal space uses are implemented.** Each recipe gives the end-to-end data path, six ordered build steps, FPGA resources and external interfaces, verification tests, and the radiation, reset, redundancy, telemetry, and recovery measures that turn a terrestrial design into a credible flight design.";

combined.manifest.description =
  "A complete beginner-to-space FPGA guide with a twelve-week learning roadmap and 30 detailed implementation recipes for spacecraft applications.";
combined.manifest.generatedAt = "2026-07-17T00:00:00Z";
combined.snapshot.generatedAt = "2026-07-17T00:00:00Z";
combined.snapshot.status = "ready";

combined.manifest.charts = uniqueById([
  ...(base.manifest.charts ?? []),
  ...(recipes.manifest.charts ?? []),
]);
combined.manifest.sources = uniqueById([
  ...(base.manifest.sources ?? []),
  ...(recipes.manifest.sources ?? []),
]);
combined.sources = uniqueById([
  ...(base.sources ?? []),
  ...(recipes.sources ?? []),
]);
combined.snapshot.datasets = {
  ...(base.snapshot.datasets ?? {}),
  ...(recipes.snapshot.datasets ?? {}),
};

fs.writeFileSync(outputPath, JSON.stringify(combined, null, 2), "utf8");

console.log(
  JSON.stringify({
    outputPath,
    blocks: combined.manifest.blocks.length,
    charts: combined.manifest.charts.length,
    sources: combined.sources.length,
    datasets: Object.keys(combined.snapshot.datasets),
    recipeBlocks: detailBlocks.filter((block) =>
      /^space_impl_use_\d+$/.test(block.id),
    ).length,
  }),
);
