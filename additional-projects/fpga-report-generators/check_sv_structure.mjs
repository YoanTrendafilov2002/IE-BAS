import fs from "node:fs";
import path from "node:path";

const directory =
  "C:/Users/user/Documents/Codex/2026-07-14/i-w/outputs/fpga_space_hdl_snippets";
const files = fs.readdirSync(directory).filter((name) => name.endsWith(".sv")).sort();
const failures = [];

function occurrences(text, pattern) {
  return [...text.matchAll(pattern)].length;
}

for (const file of files) {
  const original = fs.readFileSync(path.join(directory, file), "utf8");
  const text = original.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
  const checks = [
    ["module", occurrences(text, /\bmodule\b/g), occurrences(text, /\bendmodule\b/g)],
    ["begin", occurrences(text, /\bbegin\b/g), occurrences(text, /\bend\b/g)],
    ["case", occurrences(text, /\bcase\s*\(/g), occurrences(text, /\bendcase\b/g)],
  ];

  for (const [kind, opened, closed] of checks) {
    if (opened !== closed) failures.push(`${file}: ${kind} ${opened}/${closed}`);
  }

  const stack = [];
  const pairs = { ")": "(", "]": "[", "}": "{" };
  for (const character of text) {
    if ("([{".includes(character)) stack.push(character);
    if (")]}".includes(character) && stack.pop() !== pairs[character]) {
      failures.push(`${file}: unbalanced delimiter ${character}`);
      break;
    }
  }
  if (stack.length) failures.push(`${file}: ${stack.length} unclosed delimiters`);
}

console.log(
  JSON.stringify({
    files: files.length,
    structuralChecks: failures.length ? "failed" : "passed",
    failures,
    limitation:
      "Lexical structure only; no SystemVerilog compiler or synthesis tool is installed.",
  }),
);
process.exitCode = failures.length ? 1 : 0;
