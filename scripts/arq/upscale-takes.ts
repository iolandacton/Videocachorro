// Upscale dos takes reais na Runway (Magnific, modo mais fiel). GERAÇÃO PAGA: só com --confirmo-gasto.
// Teto: 120 créditos; tarefa com custo estimado acima disso é cancelada imediatamente.
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected node --experimental-strip-types \
//      --no-warnings scripts/arq/upscale-takes.ts --confirmo-gasto
import RunwayML, { toFile } from "@runwayml/sdk";
import { readFile, writeFile, access } from "node:fs/promises";

if (!process.argv.includes("--confirmo-gasto")) { console.error("Geração paga: rode com --confirmo-gasto"); process.exit(1); }
const TETO = 120;
const D = "public/arq_v2/takes_runway";
const destino = `${D}/saida_runway.mp4`;
if (await access(destino).then(() => true, () => false)) { console.log("saída já existe; nada a fazer."); process.exit(0); }
const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });
const antes = (await reader.organization.retrieve()).creditBalance;
console.log(`Saldo: ${antes} | teto: ${TETO}`);
const videoUri = (await reader.uploads.createEphemeral({ file: await toFile(await readFile(`${D}/entrada_512x910.mp4`), "takes.mp4") })).uri;
const t: any = await once.videoUpscale.create({
  model: "magnific_video_upscaler_creative", videoUri,
  creativity: 0, flavor: "natural", resolution: (process.env.RES ?? "720p") as any, sharpen: 0, smartGrain: 0, fpsBoost: false,
} as any);
const custo = t.estimatedCost?.credits ?? 0;
if (custo > TETO) { await once.tasks.delete(t.id); console.error(`✗ custo estimado ${custo} > teto ${TETO}. Cancelada.`); process.exit(2); }
console.log(`Tarefa ${t.id} | custo estimado ${custo} créditos`);
const done = await reader.tasks.retrieve(t.id).waitForTaskOutput();
const res = await fetch(done.output![0]);
if (!res.ok) throw new Error(`download falhou: HTTP ${res.status}`);
await writeFile(destino, Buffer.from(await res.arrayBuffer()));
const depois = (await reader.organization.retrieve()).creditBalance;
console.log(`✓ ${destino} | saldo depois: ${depois} | consumido: ${antes - depois}`);
