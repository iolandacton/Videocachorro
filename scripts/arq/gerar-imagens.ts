// Gera imagens na Runway a partir de um JSON de roteiro. GERAÇÃO PAGA.
// - Só roda com --confirmo-gasto.
// - Teto total do JSON: cada tarefa é checada pelo custo estimado e cancelada se estourar.
// - Pula imagens que já existem em public/arq/img/ (não paga duas vezes).
// - Sem novas tentativas automáticas (maxRetries=0 na criação).
// Uso: NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected \
//      node --experimental-strip-types --no-warnings scripts/arq/gerar-imagens.ts scripts/arq/imagens-previa.json --confirmo-gasto
import RunwayML, { toFile } from "@runwayml/sdk";
import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import { basename } from "node:path";

const [specPath] = process.argv.slice(2);
if (!specPath || !process.argv.includes("--confirmo-gasto")) {
  console.error("Uso: gerar-imagens.ts <spec.json> --confirmo-gasto  (geração paga)");
  process.exit(1);
}
const spec = JSON.parse(await readFile(specPath, "utf8"));
const OUT = "public/arq/img";
await mkdir(OUT, { recursive: true });

const reader = new RunwayML();
const once = new RunwayML({ maxRetries: 0 });
const antes = (await reader.organization.retrieve()).creditBalance;
console.log(`Saldo: ${antes} | teto desta execução: ${spec.teto}`);

let gasto = 0;
const registro: Record<string, unknown>[] = [];
for (const img of spec.imagens) {
  const destino = `${OUT}/${img.id}.png`;
  if (await access(destino).then(() => true, () => false)) {
    console.log(`= ${img.id}: já existe, pulando`);
    continue;
  }
  // referências opcionais: [{arquivo, tag}] → upload efêmero (gratuito), citadas no prompt como @tag
  const referenceImages = img.refs ? await Promise.all(img.refs.map(async (r: any) => ({
    tag: r.tag,
    uri: (await reader.uploads.createEphemeral({ file: await toFile(await readFile(r.arquivo), basename(r.arquivo)) })).uri,
  }))) : undefined;
  const t = await once.textToImage.create({
    model: spec.modelo,
    ratio: spec.ratio,
    promptText: `${img.prompt} ${spec.estilo}`,
    ...(referenceImages ? { referenceImages } : {}),
  } as any);
  const custo = (t as any).estimatedCost?.credits ?? 0;
  if (gasto + custo > spec.teto) {
    await once.tasks.delete(t.id);
    console.error(`✗ ${img.id}: custo ${custo} estouraria o teto (${gasto}/${spec.teto}). Cancelada.`);
    break;
  }
  gasto += custo;
  const done = await reader.tasks.retrieve(t.id).waitForTaskOutput();
  const res = await fetch(done.output![0]);
  if (!res.ok) throw new Error(`Download falhou (${img.id}): HTTP ${res.status}`);
  await writeFile(destino, Buffer.from(await res.arrayBuffer()));
  registro.push({ id: img.id, task: t.id, custo });
  console.log(`✓ ${img.id} (${custo} créditos) → ${destino}`);
}
const depois = (await reader.organization.retrieve()).creditBalance;
await writeFile(`${OUT}/registro-${basename(specPath, ".json")}.json`, JSON.stringify({ antes, depois, registro }, null, 1));
console.log(`Saldo depois: ${depois} | consumido: ${antes - depois}`);
