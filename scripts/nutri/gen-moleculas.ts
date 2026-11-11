// Reel do nutricionista — animação da REVELAÇÃO (testosterona → estradiol).
// GERAÇÃO PAGA: teto de 200 créditos, uma única tentativa (maxRetries=0).
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected \
//      node --experimental-strip-types --no-warnings scripts/nutri/gen-moleculas.ts --confirmo-gasto
import RunwayML from "@runwayml/sdk";
import { writeFile, mkdir } from "node:fs/promises";

const TETO = 200;
if (!process.argv.includes("--confirmo-gasto")) {
  console.error("Geração paga bloqueada. Rode com --confirmo-gasto após autorizar.");
  process.exit(1);
}

const PROMPT = `Abstract cinematic 3D macro animation, vertical. Glowing golden-amber molecules made of glossy spheres and thin connecting rods drift slowly through a dark, deep-black fluid with soft floating particles and shallow depth of field. As they pass through a soft translucent cloud in the center of the frame, the golden molecules smoothly morph and change color into vivid magenta-pink molecules that continue drifting forward toward the camera. Slow continuous forward camera push, volumetric light, subtle bokeh, premium medical-science visualization look. High contrast, dark background, clean composition with the action centered. No text, no letters, no numbers, no labels, no logos, no people, no organs, no syringes.`;

const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });

const antes = (await reader.organization.retrieve()).creditBalance;
console.log("Saldo antes:", antes);
if (antes < TETO) throw new Error("Saldo insuficiente; nada foi enviado.");

const created = await once.textToVideo.create({
  model: "seedance2",
  promptText: PROMPT,
  ratio: "1080:1920",
  duration: 5,
  audio: false,
});
console.log("Tarefa:", created.id, "| custo máximo informado:", created.estimatedCost.credits);
if (created.estimatedCost.credits > TETO) {
  await once.tasks.delete(created.id);
  console.error(`Custo acima do teto (${TETO}). Tarefa cancelada imediatamente.`);
  process.exit(2);
}

const task = await reader.tasks.retrieve(created.id).waitForTaskOutput();
const url = task.output![0];
console.log("Host do arquivo:", new URL(url).host);
await mkdir("out", { recursive: true });
try {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  await writeFile("out/nutri_moleculas.mp4", Buffer.from(await res.arrayBuffer()));
  console.log("Arquivo: out/nutri_moleculas.mp4");
} catch (e) {
  console.error("Geração concluída, download falhou (use scripts/download-task.ts):", String(e));
}
const depois = (await reader.organization.retrieve()).creditBalance;
console.log("Saldo depois:", depois, "| consumido:", antes - depois);
