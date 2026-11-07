import React from "react";
import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import gait from "./gait_real.json";

// CENA 01 — POV com movimento REAL transferido do vídeo do Yorkshire (6.40–10.40 s).
// Fundo: pixels originais da praia deformados só geometricamente (homografia do chão plano)
// por scripts/cena01pov/plate_motion.py. Cachorro: scripts/cena01pov/dog_layer.py (MOTION=real).
// Nenhum movimento senoidal: tudo vem de src/cena01pov/gait_real.json.
export const POV_REAL_FRAMES = gait.frames;
const pad = (f: number) => String(f).padStart(4, "0");

export const Cena01POVReal: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Img src={staticFile(`cena01pov/plate_real/p_${pad(f)}.jpg`)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      <Img src={staticFile(`cena01pov/dog_real/d_${pad(f)}.png`)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      <Audio src={staticFile("cena01pov/praia_3.5-8.5.mov")} />
    </AbsoluteFill>
  );
};
