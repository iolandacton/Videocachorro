import React from "react";
import "@fontsource/montserrat/300.css";
import "@fontsource/montserrat/400.css";
import { AbsoluteFill, Easing, Img, interpolate, random, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Outro YURI LELIS — DESIGN DE INTERIORES (5 s, 9:16).
// Fonte: dolly-in gerado no Veo 3.1 Fast a partir do quadro final aprovado, INVERTIDO (frames r_0000…r_0191,
// 24 fps): vira um dolly-out que termina exatamente na composição aprovada.
// Remapeamento de tempo: começa no macro com poros (fonte s=2,6 s) a 1,23× e desacelera até parar no
// último quadro em t=5 s. Quadros vizinhos são misturados (sem saltos). Assinatura só na pós.

const N_FRAMES = 192;
const SRC_FPS = 24;
const S0 = 2.6, V = 1.227, T_EASE = 3.8, DUR = 5;

// tempo na fonte (s) para o tempo t do vídeo: linear até 3,8 s, depois desaceleração quadrática até parar
const fonte = (t: number) => {
  if (t <= T_EASE) return S0 + V * t;
  const u = Math.min((t - T_EASE) / (DUR - T_EASE), 1);
  return S0 + V * T_EASE + V * (DUR - T_EASE) * (u - u * u / 2);
};

const quadro = (i: number) => staticFile(`outro/frames/r_${String(Math.max(0, Math.min(N_FRAMES - 1, i))).padStart(4, "0")}.jpg`);
const ease = Easing.bezier(0.45, 0, 0.2, 1);

const Grao: React.FC<{ frame: number }> = ({ frame }) => (
  <AbsoluteFill style={{ opacity: 0.06, mixBlendMode: "overlay", overflow: "hidden" }}>
    <svg width="1300" height="2200" style={{ position: "absolute",
      transform: `translate(${-110 * random(`ox${frame}`)}px, ${-140 * random(`oy${frame}`)}px)` }}>
      <filter id="og"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" /></filter>
      <rect width="100%" height="100%" filter="url(#og)" />
    </svg>
  </AbsoluteFill>
);

export const OutroYuri: React.FC<{ assinatura: boolean }> = ({ assinatura }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = fonte(t) * SRC_FPS;
  const i0 = Math.floor(s), frac = s - i0;
  // deslizamento lateral sutil sobre o macro (parede plana: equivale a mover a câmera), some até 1,6 s
  const g = interpolate(t, [0, 1.6], [1, 0], { extrapolateRight: "clamp", easing: ease });
  const camera = `translateX(${2.2 * g}%) scale(${1 + 0.035 * g})`;
  const img = { width: "100%", height: "100%", objectFit: "cover" as const, position: "absolute" as const,
    filter: "contrast(1.03) saturate(0.94) sepia(0.04)" };

  const a = interpolate(t, [3.55, 4.45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const b = interpolate(t, [3.85, 4.7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const tinta = "#2E2924";
  return (
    <AbsoluteFill style={{ background: "#d9cdbd" }}>
      <AbsoluteFill style={{ transform: camera }}>
        <Img src={quadro(i0)} style={img} />
        <Img src={quadro(i0 + 1)} style={{ ...img, opacity: frac }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 55%, rgba(30,22,14,0.22) 100%)" }} />
      <Grao frame={frame} />
      {assinatura && (
        <AbsoluteFill style={{ alignItems: "center", fontFamily: "Montserrat, sans-serif", color: tinta }}>
          <div style={{ position: "absolute", top: 744, textAlign: "center" }}>
            <div style={{ fontWeight: 400, fontSize: 78, opacity: a, transform: `translateY(${10 * (1 - a)}px)`,
              letterSpacing: `${0.44 - 0.06 * a}em`, paddingLeft: `${0.44 - 0.06 * a}em` }}>YURI LELIS</div>
            <div style={{ height: 1.5, background: tinta, opacity: 0.55 * b, width: 140 * b, margin: "34px auto 30px" }} />
            <div style={{ fontWeight: 300, fontSize: 25, opacity: b, letterSpacing: "0.55em", paddingLeft: "0.55em",
              transform: `translateY(${6 * (1 - b)}px)` }}>DESIGN DE INTERIORES</div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
