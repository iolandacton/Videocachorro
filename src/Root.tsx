import { Composition } from "remotion";
import { Main } from "./Main";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Main"
    component={Main}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ titulo: "Videocachorro" }}
  />
);
