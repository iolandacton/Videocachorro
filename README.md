# Videocachorro

Vídeos programáticos com [Remotion](https://www.remotion.dev) + geração com a [API da Runway](https://docs.dev.runwayml.com).

## Comandos

| Comando | O que faz |
|---|---|
| `npm install` | Instala as dependências |
| `npm run studio` | Abre o Remotion Studio (editor no navegador) |
| `npm run still` | Renderiza um quadro em `out/frame.png` |
| `npm run render` | Renderiza o vídeo em `out/video.mp4` (1080x1920, 30fps) |
| `npm run typecheck` | Verifica os tipos TypeScript |
| `npm run runway:check` | Mostra os créditos da conta Runway (gratuito, não gera nada) |

## Runway

1. Crie uma chave em https://dev.runwayml.com.
2. Copie `.env.example` para `.env` e preencha `RUNWAYML_API_SECRET` (o `.env` não é commitado).
3. **No Claude Code na nuvem (ambiente "Videocachorro")**: a chave fica salva como segredo de rede
   e o proxy a injeta nas requisições. Não crie `.env`; rode com:
   `NODE_USE_ENV_PROXY=1 RUNWAYML_API_SECRET=proxy-injected npm run runway:check`
4. Toda geração (`imageToVideo`, `textToImage` etc.) **gasta créditos**: confirme antes de rodar.
