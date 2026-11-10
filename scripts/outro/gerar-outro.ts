// Outro YURI LELIS — DESIGN DE INTERIORES. GERAÇÃO PAGA, só com --confirmo-gasto.
// Etapa "imagem": quadro final (sala) em gen4_image.  Etapa "video": Veo 3.1 parte desse quadro e
// faz um dolly-in até o macro do travertino; na pós o vídeo é invertido (dolly-out que termina
// exatamente na composição aprovada). Teto total por execução; tarefa acima do teto é cancelada.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected node --experimental-strip-types \
//      --no-warnings scripts/outro/gerar-outro.ts imagem|video --confirmo-gasto
import RunwayML, { toFile } from "@runwayml/sdk";
import { readFile, writeFile, mkdir, access } from "node:fs/promises";

const [etapa] = process.argv.slice(2);
if (!["imagem", "video"].includes(etapa) || !process.argv.includes("--confirmo-gasto")) {
  console.error("Uso: gerar-outro.ts imagem|video --confirmo-gasto  (geração paga)");
  process.exit(1);
}
const TETO = etapa === "imagem" ? 10 : 122;
const DIR = "public/outro";
await mkdir(DIR, { recursive: true });
const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });
const existe = (p: string) => access(p).then(() => true, () => false);
const antes = (await reader.organization.retrieve()).creditBalance;
console.log(`Saldo: ${antes} | teto desta etapa: ${TETO}`);

const QUADRO = `${DIR}/quadro_final.png`;
const PROMPT_IMG = "Vertical architectural photograph of an elegant contemporary living room. Centered, symmetrical composition: a floor-to-ceiling wall clad in large slabs of authentic honed beige travertine, with its characteristic small natural pits, pores and soft horizontal linear banding (not marble, no veins), fills the middle of the frame as calm, clean negative space, softly grazed by warm late-afternoon sunlight from a tall window on the left. In the lower third: a low linen sofa in warm off-white, a light oak coffee table and a small natural stone sculpture. Light oak floor, subtle hidden architectural cove lighting along the ceiling edge, warm neutral tones. Timeless, minimal, luxurious residential interior photographed with a Sony FX3 and a 35mm lens, realistic depth of field, physically accurate light, editorial interior photography, premium neutral color grade. No people, no text, no logos, no watermark.";
const PROMPT_VID = "Physically realistic cinematic camera move filmed on a Sony FX3 with a 35mm lens. The shot starts perfectly still on this living room, then the camera performs one very smooth, continuous dolly-in straight toward the center of the beige travertine wall, gently accelerating and then easing as it arrives at an extreme macro close-up of the travertine surface, where warm late-afternoon sunlight rakes across its natural pores and imperfections. It ends with a slow, subtle lateral glide across the stone texture. Static scene: nothing moves except the camera. Walls, furniture and stone keep perfectly rigid, accurate geometry. Realistic shallow depth of field, subtle film grain, premium neutral grading.";
const NEGATIVO = "CGI, 3D render look, morphing, warping, melting, bending or distorted architecture, flicker, text, letters, logo, watermark, lens flare, people, cuts, transitions, zoom blur";

async function custoOk(t: { id: string; estimatedCost?: { credits: number } }, gasto: number) {
  const c = t.estimatedCost?.credits ?? 0;
  if (gasto + c > TETO) {
    await once.tasks.delete(t.id);
    console.error(`✗ custo estimado ${c} passaria do teto (${TETO}). Tarefa cancelada.`);
    return -1;
  }
  return c;
}

if (etapa === "imagem") {
  if (await existe(QUADRO)) { console.log("quadro_final.png já existe; nada a fazer."); process.exit(0); }
  const t: any = await once.textToImage.create({ model: "gen4_image", ratio: "1080:1920", promptText: PROMPT_IMG } as any);
  if ((await custoOk(t, 0)) < 0) process.exit(2);
  const done = await reader.tasks.retrieve(t.id).waitForTaskOutput();
  await writeFile(QUADRO, Buffer.from(await (await fetch(done.output![0])).arrayBuffer()));
  console.log(`✓ ${QUADRO} (tarefa ${t.id})`);
} else {
  const destino = `${DIR}/dolly_in_veo.mp4`;
  if (await existe(destino)) { console.log("dolly_in_veo.mp4 já existe; nada a fazer."); process.exit(0); }
  const uri = (await reader.uploads.createEphemeral({ file: await toFile(await readFile(QUADRO), "quadro.png") })).uri;
  let t: any = null;
  for (const model of ["veo3.1", "veo3.1_fast"]) {  // melhor qualidade primeiro; o rápido só se o primeiro estourar o teto
    t = await once.imageToVideo.create({ model, promptImage: [{ uri, position: "first" }], promptText: PROMPT_VID,
      negativePrompt: NEGATIVO, ratio: "1080:1920", duration: 8, audio: false } as any);
    const c = await custoOk(t, 0);
    if (c >= 0) { console.log(`modelo ${model}: custo estimado ${c} créditos`); break; }
    t = null;
  }
  if (!t) process.exit(2);
  const done = await reader.tasks.retrieve(t.id).waitForTaskOutput();
  await writeFile(destino, Buffer.from(await (await fetch(done.output![0])).arrayBuffer()));
  console.log(`✓ ${destino} (tarefa ${t.id})`);
}
const depois = (await reader.organization.retrieve()).creditBalance;
console.log(`Saldo depois: ${depois} | consumido: ${antes - depois}`);
