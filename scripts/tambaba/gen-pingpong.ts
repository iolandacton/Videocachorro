// Guia Casa Tambaba — animação do tampo de ping-pong indo para o suporte.
// GERAÇÃO PAGA: teto total de 150 créditos, uma tentativa por etapa (maxRetries=0).
//   1. gpt_image_2 edita a foto real (tampo guardado) para o tampo ficar EM CIMA da mesa -> 1º quadro
//   2. veo3.1_fast anima do 1º quadro até a foto real (tampo no suporte) -> último quadro
// Etapas já feitas (arquivo existe) não são refeitas.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected \
//      node --experimental-strip-types --no-warnings scripts/tambaba/gen-pingpong.ts --confirmo-gasto
import RunwayML from "@runwayml/sdk";
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";

const TETO = 150;
const DIR = "guia-tambaba/videos";
if (!process.argv.includes("--confirmo-gasto")) {
  console.error("Geração paga bloqueada. Rode com --confirmo-gasto após autorizar.");
  process.exit(1);
}

const PROMPT_QUADRO = `Edit @foto. Keep everything exactly as in @foto: same room, camera angle, framing, lighting, wooden doors, walls, floor tiles, wall lamp, the pool table, the small dog under the table, the four wooden billiard cues standing in the black wall cue rack, and the low black U-shaped wooden floor stand on the floor against the wall below the cue rack. Change only this: the two black ping-pong table halves (black boards with thin white edge lines, currently leaning in the floor stand against the wall) are now lying flat on top of the pool table, side by side, covering the whole green felt and forming one complete ping-pong playing surface with a thin white center line. The black floor stand stays in place but is now empty, so its low black U shape is fully visible against the wall. Photorealistic, same photo look and colors.`;

const PROMPT_VIDEO = `Static locked-off camera, photorealistic home video look. The two black ping-pong table halves resting on top of the pool table lift up one at a time, float smoothly across to the black floor stand against the wall and settle standing upright in it, side by side, revealing the green felt of the pool table. Gentle, clear, satisfying motion. Nothing else in the room moves; the small dog under the table stays still. No people, no hands.`;

const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });
const dataUri = async (p: string) => "data:image/jpeg;base64," + (await readFile(p)).toString("base64");

type Criada = { id: string; estimatedCost: { credits: number } };
let gasto = 0;
async function rodar(nome: string, criar: () => Promise<Criada>): Promise<string> {
  const t = await criar();
  console.log(`[${nome}] tarefa ${t.id} | custo máximo: ${t.estimatedCost.credits}`);
  if (gasto + t.estimatedCost.credits > TETO) {
    await once.tasks.delete(t.id);
    throw new Error(`[${nome}] passaria do teto de ${TETO} créditos. Tarefa cancelada.`);
  }
  gasto += t.estimatedCost.credits;
  const pronto = await reader.tasks.retrieve(t.id).waitForTaskOutput();
  return pronto.output![0] as string;
}
async function baixar(url: string, destino: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  await writeFile(destino, Buffer.from(await res.arrayBuffer()));
  console.log("Arquivo:", destino);
}

const antes = (await reader.organization.retrieve()).creditBalance;
console.log("Saldo antes:", antes);

const ultimo = `${DIR}/fontes/pingpong_guardado.jpg`; // foto real recortada em 1080x1920
const primeiroPng = `${DIR}/fontes/pingpong_na_mesa.png`;
const primeiro = `${DIR}/fontes/pingpong_na_mesa.jpg`;
const video = `${DIR}/pingpong_animacao.mp4`;

// 1. primeiro quadro: tampo em cima da mesa
if (!existsSync(primeiro)) {
  const foto = await dataUri(ultimo);
  const url = await rodar("quadro", () =>
    once.textToImage.create({
      model: "gpt_image_2",
      ratio: "1088:1920",
      quality: "high",
      referenceImages: [{ uri: foto, tag: "foto" }],
      promptText: PROMPT_QUADRO,
    })
  );
  await baixar(url, primeiroPng);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", primeiroPng, "-vf", "scale=1080:1920", "-q:v", "2", primeiro]);
  if (process.argv.includes("--so-quadro")) process.exit(0);
}

// 2. animação do primeiro ao último quadro
if (!existsSync(video)) {
  const a = await dataUri(primeiro);
  const b = await dataUri(ultimo);
  const url = await rodar("video", () =>
    once.imageToVideo.create({
      model: "veo3.1_fast",
      ratio: "720:1280",
      duration: 8,
      audio: false,
      promptImage: [{ uri: a, position: "first" }, { uri: b, position: "last" }],
      promptText: PROMPT_VIDEO,
      negativePrompt: "people, hands, camera movement, zoom, distortion, warping, extra objects, text",
    })
  );
  await baixar(url, video);
}

const depois = (await reader.organization.retrieve()).creditBalance;
console.log("Saldo depois:", depois, "| consumido:", antes - depois);
