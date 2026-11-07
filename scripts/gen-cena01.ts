// CENA 01 — POV do Yorkshire na praia (prévia de 5 s, 9:16, com áudio).
// GERAÇÃO PAGA: só roda com a flag --confirmo-gasto.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected \
//      node --experimental-strip-types --no-warnings scripts/gen-cena01.ts --confirmo-gasto
import RunwayML, { toFile } from "@runwayml/sdk";
import { readFile, writeFile, mkdir } from "node:fs/promises";

if (!process.argv.includes("--confirmo-gasto")) {
  console.error("Geração paga bloqueada. Rode com --confirmo-gasto após autorizar.");
  process.exit(1);
}

const PROMPT = `Photorealistic first-person action-camera footage. The camera is physically strapped to the back of a small Yorkshire Terrier, slightly above its back, pointing forward. The bottom of the frame always shows the dog from behind exactly as in the reference photo: top of the head with tan/golden-brown long silky hair tied in a small topknot with a black elastic, small upright ears covered in long wet tan hair, and a short stretch of black/dark steel-blue wet fur on the back. The dog trots naturally forward across the wet, reflective sand of this exact beach (0-1s), approaches the waterline and its front paws touch the thin sheet of water (1-3s), then keeps trotting through very shallow water with small splashes (3-5s). Keep the same beach, deep blue sky, white clouds, palm trees on the left horizon, sunlight and horizon line as the input video. Natural subtle bobbing from the dog's gait, action-camera stabilization, no impossible camera moves. No people, no extra limbs, no deformation, no text, no logos, not cartoonish, not CGI. Natural audio only, no music: soft waves in the background, quick small paws on wet sand, light splashes synced with the steps, gentle breeze.`;

const client = new RunwayML();
const up = async (path: string, name: string) =>
  (await client.uploads.createEphemeral({ file: await toFile(await readFile(path), name) })).uri;

const promptVideo = await up("refs/cena01/praia_base_2-7s.mp4", "praia.mp4");
const dog = await up("refs/cena01/yorkshire_costas.jpg", "yorkshire.jpg");

const task = await client.videoToVideo
  .create({
    model: "seedance2",
    promptVideo,
    promptText: PROMPT,
    references: [{ uri: dog }],
    ratio: "1080:1920",
    duration: 5,
    audio: true,
  })
  .waitForTaskOutput();

await mkdir("out", { recursive: true });
const res = await fetch(task.output![0]);
await writeFile("out/cena01_runway.mp4", Buffer.from(await res.arrayBuffer()));
console.log("Task:", task.id, "→ out/cena01_runway.mp4");
