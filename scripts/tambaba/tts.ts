// Guia Casa Tambaba — narração com voz feminina (Runway text-to-speech, ElevenLabs multilíngue).
// GERAÇÃO PAGA (barata): teto de 10 créditos por chamada, sem novas tentativas.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected \
//      node --experimental-strip-types --no-warnings scripts/tambaba/tts.ts --confirmo-gasto <voz> <saida.mp3> "<texto>"
import RunwayML from "@runwayml/sdk";
import { writeFile } from "node:fs/promises";

const TETO = 10;
const args = process.argv.slice(2).filter((a) => a !== "--confirmo-gasto");
if (!process.argv.includes("--confirmo-gasto") || args.length !== 3) {
  console.error('Uso: tts.ts --confirmo-gasto <voz> <saida.mp3> "<texto>"');
  process.exit(1);
}
const [voz, saida, texto] = args;
const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });

const t = await once.textToSpeech.create({
  model: "eleven_multilingual_v2",
  promptText: texto,
  voice: { type: "runway-preset", presetId: voz as "Rachel" },
});
console.log(`[tts ${voz}] tarefa ${t.id} | custo máximo: ${t.estimatedCost.credits}`);
if (t.estimatedCost.credits > TETO) {
  await once.tasks.delete(t.id);
  throw new Error("Custo acima do teto; tarefa cancelada.");
}
const pronto = await reader.tasks.retrieve(t.id).waitForTaskOutput();
const res = await fetch(pronto.output![0] as string);
if (!res.ok) throw new Error(`HTTP ${res.status}`);
await writeFile(saida, Buffer.from(await res.arrayBuffer()));
console.log("Arquivo:", saida);
