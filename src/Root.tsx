import { Composition } from "remotion";
import { Main } from "./Main";
import { Cena01Preview } from "./Cena01Preview";
import { Chegada, CHEGADA_FRAMES } from "./cena01/Chegada";
import { Cena01POV } from "./cena01pov/Cena01POV";
import { Cena01POVReal, POV_REAL_FRAMES } from "./cena01pov/Cena01POVReal";
import { Arquitetura, type Roteiro } from "./arquitetura/Arquitetura";
import previa from "./arquitetura/previa.json";
import final from "./arquitetura/final.json";
import { ArquiteturaV2, type Roteiro as RoteiroV2 } from "./arquitetura/v2/ArquiteturaV2";
import finalV2 from "./arquitetura/v2/final_v2.json";
import finalV2q from "./arquitetura/v2/final_v2q.json";
import finalV3 from "./arquitetura/v2/final_v3.json";
import { OutroYuri } from "./outro/OutroYuri";
import { Oficina, type RoteiroOficina } from "./oficina/Oficina";
import roteiroOficina from "./oficina/roteiro.json";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Main" component={Main} durationInFrames={90} fps={30}
      width={1080} height={1920} defaultProps={{ titulo: "Videocachorro" }} />
    <Composition id="Cena01Preview" component={Cena01Preview} durationInFrames={150}
      fps={30} width={1080} height={1920} />
    <Composition id="Cena01Chegada" component={Chegada} durationInFrames={CHEGADA_FRAMES}
      fps={30} width={1080} height={1920} />
    <Composition id="Cena01POV" component={Cena01POV} durationInFrames={150}
      fps={30} width={1080} height={1920} />
    <Composition id="Cena01POVReal" component={Cena01POVReal} durationInFrames={POV_REAL_FRAMES}
      fps={30} width={1080} height={1920} />
    <Composition id="ArqPrevia" component={Arquitetura}
      durationInFrames={Math.round(previa.duracao * previa.fps)} fps={previa.fps} width={1080} height={1920}
      defaultProps={{ roteiro: previa as unknown as Roteiro, audio: "arq/previa/audio.wav" }} />
    <Composition id="ArqFinal" component={Arquitetura}
      durationInFrames={Math.round(final.duracao * final.fps)} fps={final.fps} width={1080} height={1920}
      defaultProps={{ roteiro: final as unknown as Roteiro, audio: "arq/final/audio.wav" }} />
    {/* V2: cópia de trabalho para as prévias A–D. A ArqFinal acima continua sendo a versão aprovada. */}
    <Composition id="ArqV2" component={ArquiteturaV2}
      durationInFrames={Math.round(finalV2.duracao * finalV2.fps)} fps={finalV2.fps} width={1080} height={1920}
      defaultProps={{ roteiro: finalV2 as unknown as RoteiroV2, audio: "arq_v2/mix/audio.wav" }} />
    {/* V2Q: mesma edição v2 com os vídeos reais do Yuri em qualidade recuperada (prévias de qualidade) */}
    <Composition id="ArqV2Q" component={ArquiteturaV2}
      durationInFrames={Math.round(finalV2q.duracao * finalV2q.fps)} fps={finalV2q.fps} width={1080} height={1920}
      defaultProps={{ roteiro: finalV2q as unknown as RoteiroV2, audio: "arq_v2/mix/audio.wav" }} />
    {/* V3: v2 aprovada + vídeos reais em qualidade recuperada (intro sem IA; takes com upscale Runway, exceto IMG_2723) */}
    <Composition id="ArqV3" component={ArquiteturaV2}
      durationInFrames={Math.round(finalV3.duracao * finalV3.fps)} fps={finalV3.fps} width={1080} height={1920}
      defaultProps={{ roteiro: finalV3 as unknown as RoteiroV2, audio: "arq_v2/mix/audio.wav" }} />
    <Composition id="OutroYuri" component={OutroYuri} durationInFrames={120} fps={24} width={1080} height={1920}
      defaultProps={{ assinatura: true }} />
    {/* mesmo encerramento a 30 fps (igual ao vídeo principal), saindo do preto, para a versão completa */}
    <Composition id="OutroYuri30" component={OutroYuri} durationInFrames={150} fps={30} width={1080} height={1920}
      defaultProps={{ assinatura: true, entradaPreto: 0.4 }} />
    {/* Oficina Sete — primeira montagem (prévia) */}
    <Composition id="Oficina" component={Oficina}
      durationInFrames={Math.round(roteiroOficina.duracao * roteiroOficina.fps)} fps={roteiroOficina.fps} width={1080} height={1920}
      defaultProps={{ roteiro: roteiroOficina as unknown as RoteiroOficina, audio: "oficina/mix/audio.wav" }} />
  </>
);
