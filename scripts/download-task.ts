// Baixa a saída de uma tarefa Runway JÁ CONCLUÍDA (gratuito, não gera nada).
// Uso: node --experimental-strip-types --no-warnings scripts/download-task.ts <taskId> <arquivo.mp4>
import RunwayML from "@runwayml/sdk";
import { writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const [id, dest] = process.argv.slice(2);
const t: any = await new RunwayML().tasks.retrieve(id);
if (t.status !== "SUCCEEDED") throw new Error(`Tarefa não concluída: ${t.status}`);
const res = await fetch(t.output[0]);
if (!res.ok) throw new Error(`Download falhou: HTTP ${res.status}`);
await mkdir(dirname(dest), { recursive: true });
await writeFile(dest, Buffer.from(await res.arrayBuffer()));
console.log("Salvo:", dest);
