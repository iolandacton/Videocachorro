// Encerramento OFICINA 7 — fundo de marcenaria de alto padrão para a logo. GERAÇÃO PAGA, só com --confirmo-gasto.
// Etapa "imagem": quadro final (painel ripado de carvalho, centro escuro para a logo) em gen4_image. Etapa "video":
// Veo 3.1 parte desse quadro e avança até o macro da madeira; na pós o vídeo é invertido (termina
// exatamente no quadro da logo, que é aplicada no Remotion — a logo real, nunca gerada por IA). Teto por etapa.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected node --experimental-strip-types \
//      --no-warnings scripts/oficina/gerar-outro.ts imagem|video --confirmo-gasto
import RunwayML, { toFile } from "@runwayml/sdk";
import { readFile, writeFile, mkdir, access } from "node:fs/promises";

const [etapa] = process.argv.slice(2);
if (!["imagem", "video"].includes(etapa) || !process.argv.includes("--confirmo-gasto")) {
  console.error("Uso: gerar-outro.ts imagem|video --confirmo-gasto  (geração paga)");
  process.exit(1);
}
const TETO = etapa === "imagem" ? 10 : 90;
const DIR = "public/oficina/outro";
await mkdir(DIR, { recursive: true });
const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });
const existe = (p: string) => access(p).then(() => true, () => false);
const antes = (await reader.organization.retrieve()).creditBalance;
console.log(`Saldo: ${antes} | teto desta etapa: ${TETO}`);

const QUADRO = `${DIR}/quadro_final.png`;
const PROMPT_IMG = "Vertical cinematic low-key photograph of premium bespoke millwork in a dark, quiet showroom. A tall wall panel of natural light oak with precise CNC-milled vertical slats fills the frame, perfectly straight and evenly spaced, matte oiled finish with fine visible wood grain. A single narrow beam of warm light grazes the slats from the upper left, so the left third glows softly in warm honey tones while the centre and right of the frame fall gradually into deep, soft, clean shadow: a large calm dark area in the middle of the frame. A thin warm LED line glows faintly along the bottom edge. Elegant, minimal, luxurious high-end carpentry. Photographed with a Sony FX3 and a 50mm lens, shallow depth of field, physically accurate light, subtle film grain, premium warm-neutral color grade. No people, no furniture, no text, no letters, no logos, no watermark.";
const PROMPT_VID = "Physically realistic cinematic camera move filmed on a Sony FX3 with a macro-capable 50mm lens. The shot starts perfectly still on this dark oak slatted panel, then the camera performs one very smooth, continuous, slow dolly-in toward the softly lit left side of the panel while gliding gently to the left, easing as it arrives at an extreme macro close-up of the milled oak slats, where the warm light rakes across the fine wood grain and the crisp machined edges. A few tiny dust particles drift slowly in the light beam. Static scene: nothing moves except the camera and the dust. The slats keep perfectly straight, rigid, accurate geometry and even spacing. Realistic shallow depth of field, subtle film grain, premium warm-neutral grading.";
const NEGATIVO = "CGI, 3D render look, morphing, warping, melting, bending or wavy slats, changing slat count, flicker, text, letters, logo, watermark, lens flare, people, hands, tools, cuts, transitions, zoom blur";

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
  for (const model of ["veo3.1_fast"]) {
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
