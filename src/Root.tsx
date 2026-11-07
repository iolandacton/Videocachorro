import { Composition } from "remotion";
import { Main } from "./Main";
import { Cena01Preview } from "./Cena01Preview";
import { Chegada, CHEGADA_FRAMES } from "./cena01/Chegada";
import { Cena01POV } from "./cena01pov/Cena01POV";

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
  </>
);
