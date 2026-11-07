// Verificação GRATUITA da conta Runway: lê apenas os créditos/limites da organização.
// NÃO gera nada e NÃO gasta créditos. Requer RUNWAYML_API_SECRET no ambiente.
import RunwayML from "@runwayml/sdk";

const client = new RunwayML(); // lê RUNWAYML_API_SECRET
const org = await client.organization.retrieve();
console.log("Créditos disponíveis:", org.creditBalance);
