import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import trot from "./trot.json";

// CENA 01 — POV do Yorkshire (composição convencional, sem IA generativa).
// Fundo: pixels reais da Insta360 (3.5–8.5 s), apenas recortados para tirar a marca d'água.
// Câmera presa às costas: o MUNDO oscila no ritmo do trote; o dorso do cachorro fica fixo.
// A camada do cachorro (cabeça/orelhas/pelo animados) vem de scripts/cena01pov/dog_layer.py.

const { fps, strideHz, camera } = trot;

const cameraAt = (f: number) => {
  const t = f / fps;
  const ph = 2 * Math.PI * strideHz * t;
  // mesma modulação de amplitude da camada do cachorro (passos não idênticos)
  const amp = 1 + 0.15 * Math.sin(2 * Math.PI * 0.7 * t) + 0.05 * Math.sin(2 * Math.PI * 1.9 * t);
  // corpo sobe 2x por passada (apoios diagonais) → mundo desce/sobe no quadro
  const y = camera.bounceY * amp * (Math.sin(2 * ph) + 0.2 * Math.sin(4 * ph + 0.7));
  // balanço lateral e rolagem 1x por passada (estabilização de action cam já amortece)
  const x = camera.swayX * amp * Math.sin(ph + 0.4);
  const roll = camera.rollDeg * amp * Math.sin(ph + 0.9);
  return { x, y, roll };
};

export const Cena01POV: React.FC = () => {
  const f = useCurrentFrame();
  const { x, y, roll } = cameraAt(f);
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{
        transform: `translate(${x}px, ${y}px) rotate(${roll}deg) scale(${camera.scale})`,
      }}>
        <OffthreadVideo muted src={staticFile("cena01pov/praia_3.5-8.5.mov")}
          style={{ width: "100%", height: "100%" }} />
      </AbsoluteFill>
      <Img src={staticFile(`cena01pov/dog/d_${String(f).padStart(4, "0")}.png`)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      {/* Som original da gravação (mar e vento) */}
      <Audio src={staticFile("cena01pov/praia_3.5-8.5.mov")} />
    </AbsoluteFill>
  );
};
