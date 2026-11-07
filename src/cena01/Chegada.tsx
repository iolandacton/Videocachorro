import React from "react";
import {
  AbsoluteFill, Audio, Img, Sequence, interpolate, Easing,
  staticFile, useCurrentFrame,
} from "remotion";

// CENA 01 — Chegada cinematográfica à praia.
// Material: vídeo real Insta360 X6 (reenquadrado, 512x910 → upscale 1080x1920).
// Os frames vêm de scripts/cena01/prepare.sh (recorte + cor + lanczos).
// Cada trecho tem rampa de velocidade linear: velocidade s0 → s1 ao longo da duração.

const FPS = 30;
const SRC_FPS = 30;

type Seg = {
  id: string;
  src: number; // início na fonte (s)
  dur: number; // duração na saída (s)
  s0: number; // velocidade inicial
  s1: number; // velocidade final
  min: number; // primeiro frame disponível (índice da fonte)
  max: number; // último frame disponível
  zoom: [number, number]; // zoom digital início → fim
  origin?: string; // ponto de ancoragem do zoom (ex.: areia na parte de baixo)
  zoomEase?: (t: number) => number;
};

// Faixas extraídas por prepare.sh (índices a 30 fps)
const R1 = [12, 212], R2 = [672, 875], R3 = [957, 1805], R4 = [2643, 2783], R5 = [3117, 3407];

const SEGS: Seg[] = [
  // A — abertura sob a vegetação, avanço suave
  { id: "A", src: 0.5, dur: 2.5, s0: 1, s1: 1, min: R1[0], max: R1[1], zoom: [1.0, 1.06] },
  // B1 — aceleração até o portão preencher o quadro (corte por ocultação)
  { id: "B1", src: 3.0, dur: 2.0, s0: 1, s1: 3, min: R1[0], max: R1[1], zoom: [1.06, 1.14],
    zoomEase: Easing.in(Easing.quad) },
  // B2 — caminho sob os galhos; termina com folhas cobrindo a lente
  { id: "B2", src: 24.6, dur: 1.9, s0: 2.0, s1: 2.63, min: R2[0], max: R2[1], zoom: [1.04, 1.1] },
  // C — rasante pelo caminho de areia com coqueiros
  { id: "C", src: 32.0, dur: 3.0, s0: 5, s1: 11.67, min: R3[0], max: R3[1], zoom: [1.06, 1.22],
    zoomEase: Easing.in(Easing.quad) },
  // D1 — mesmo plano contínuo: desacelera quando a praia se abre
  { id: "D1", src: 57.0, dur: 0.8, s0: 6, s1: 1.5, min: R3[0], max: R3[1], zoom: [1.22, 1.08],
    zoomEase: Easing.out(Easing.cubic) },
  // D2 — match cut para a revelação do mar, leve câmera lenta
  { id: "D2", src: 88.2, dur: 4.4, s0: 1.25, s1: 0.75, min: R4[0], max: R4[1], zoom: [1.0, 1.07] },
  // E — mergulho digital na areia úmida + aceleração e blur final (gancho p/ o Yorkshire)
  { id: "E", src: 105.5, dur: 2.5, s0: 1, s1: 5.0, min: R5[0], max: R5[1], zoom: [1.03, 2.6],
    origin: "50% 100%", zoomEase: Easing.in(Easing.quad) },
];

// Início de cada trecho em frames da saída
const STARTS: number[] = [];
let acc = 0;
for (const s of SEGS) { STARTS.push(acc); acc += Math.round(s.dur * FPS); }
export const CHEGADA_FRAMES = acc;

const srcAt = (s: Seg, t: number) => s.src + s.s0 * t + ((s.s1 - s.s0) * t * t) / (2 * s.dur);
const speedAt = (s: Seg, t: number) => s.s0 + ((s.s1 - s.s0) * t) / s.dur;
const fileFor = (i: number) => staticFile(`cena01/frames/f_${String(i).padStart(5, "0")}.jpg`);

// Motion blur por mistura de frames da fonte: obturador de 180°.
const MotionBlurFrame: React.FC<{ seg: Seg; t: number; extraBlur: number }> = ({ seg, t, extraBlur }) => {
  const speed = speedAt(seg, t);
  const center = srcAt(seg, t) * SRC_FPS;
  const span = (speed * SRC_FPS) / FPS / 2; // frames da fonte cobertos pelo obturador
  const n = Math.max(1, Math.min(7, Math.round(span)));
  const idxs = Array.from({ length: n }, (_, k) => {
    const raw = n === 1 ? center : center - span / 2 + (span * k) / (n - 1);
    return Math.max(seg.min, Math.min(seg.max, Math.round(raw)));
  });
  return (
    <AbsoluteFill style={{ filter: extraBlur > 0.05 ? `blur(${extraBlur}px)` : undefined }}>
      {idxs.map((idx, k) => (
        <AbsoluteFill key={k} style={{ opacity: 1 / (k + 1) }}>
          <Img src={fileFor(idx)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      ))}
    </AbsoluteFill>
  );
};

const SegmentView: React.FC<{ seg: Seg; i: number }> = ({ seg, i }) => {
  const f = useCurrentFrame(); // relativo à Sequence
  const total = Math.round(seg.dur * FPS);
  const t = f / FPS;
  const u = Math.min(1, f / (total - 1));
  const ease = seg.zoomEase ?? ((x: number) => x);
  const z = interpolate(ease(u), [0, 1], seg.zoom);

  // "Soco" de câmera nos cortes importantes (entrada de B2, C, D2)
  const punch = ["B2", "C", "D2"].includes(seg.id)
    ? interpolate(f, [0, 7], [1.045, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) })
    : 1;

  // Blur extra só onde a velocidade justifica: fim de B1 (whoosh no portão) e saída de E
  let extraBlur = 0;
  if (seg.id === "B1") extraBlur = interpolate(f, [total - 5, total - 1], [0, 6], { extrapolateLeft: "clamp" });
  if (seg.id === "B2") extraBlur = interpolate(f, [0, 4], [5, 0], { extrapolateRight: "clamp" });
  if (seg.id === "E") extraBlur = interpolate(f, [total - 14, total - 1], [0, 14], {
    extrapolateLeft: "clamp", easing: Easing.in(Easing.quad) });

  // Pequena trepidação de action cam apenas no rasante
  const shake = seg.id === "C" ? Math.sin(f * 2.3) * 3 + Math.sin(f * 5.1) * 1.5 : 0;

  return (
    <AbsoluteFill style={{
      transform: `translateY(${shake}px) scale(${z * punch})`,
      transformOrigin: seg.origin ?? "50% 50%",
    }}>
      <MotionBlurFrame seg={seg} t={t} extraBlur={extraBlur} />
    </AbsoluteFill>
  );
};

// Áudio: [arquivo, frame inicial, volume]
const sfx = (name: string) => staticFile(`cena01/audio/${name}.wav`);
const S = (id: string) => STARTS[SEGS.findIndex((s) => s.id === id)];

export const Chegada: React.FC = () => {
  const f = useCurrentFrame();
  // Vinheta suave, mais forte na abertura misteriosa
  const vignette = interpolate(f, [0, 75, 120], [0.55, 0.45, 0.32], { extrapolateRight: "clamp" });
  // Abertura a partir do preto
  const fadeIn = interpolate(f, [0, 10], [1, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {SEGS.map((seg, i) => (
        <Sequence key={seg.id} from={STARTS[i]} durationInFrames={Math.round(seg.dur * FPS)}>
          <SegmentView seg={seg} i={i} />
        </Sequence>
      ))}

      <AbsoluteFill style={{
        background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,${vignette}) 100%)`,
      }} />
      <AbsoluteFill style={{ backgroundColor: "black", opacity: fadeIn }} />

      {/* Som natural */}
      <Sequence from={0} durationInFrames={S("B1") + 20}><Audio src={sfx("amb_arvores")} /></Sequence>
      <Sequence from={0} durationInFrames={105}><Audio src={sfx("folhas")} volume={0.8} /></Sequence>
      <Sequence from={S("B1")} durationInFrames={60}><Audio src={sfx("passos_areia")} volume={0.55} /></Sequence>
      {/* Vento crescendo do acesso até a revelação */}
      <Sequence from={S("B2") - 10} durationInFrames={S("D2") - S("B2") + 10}>
        <Audio src={sfx("vento_crescente")} volume={(fr) =>
          interpolate(fr, [0, 150, 168, 175], [0.6, 0.9, 0.9, 0], { extrapolateRight: "clamp" })} />
      </Sequence>
      {/* Whooshes sincronizados aos cortes por ocultação/aceleração */}
      <Sequence from={S("B2") - 7}><Audio src={sfx("whoosh")} volume={0.75} /></Sequence>
      <Sequence from={S("C") - 7}><Audio src={sfx("whoosh")} volume={0.85} /></Sequence>
      <Sequence from={S("E") + 60}><Audio src={sfx("whoosh")} volume={0.9} /></Sequence>
      {/* Impactos suaves nos cortes principais */}
      <Sequence from={S("C")}><Audio src={sfx("impacto")} volume={0.5} /></Sequence>
      <Sequence from={S("D2")}><Audio src={sfx("impacto")} volume={0.8} /></Sequence>
      {/* Mar cresce na revelação */}
      <Sequence from={S("D2") - 4} durationInFrames={Math.round(4.4 * FPS) + 4}>
        <Audio src={sfx("mar_revelacao")} volume={(fr) =>
          interpolate(fr, [0, 10, 125, 136], [0.3, 1, 1, 0.7], { extrapolateRight: "clamp" })} />
      </Sequence>
      <Sequence from={S("E")} durationInFrames={Math.round(2.5 * FPS)}>
        <Audio src={sfx("mar_areia")} volume={(fr) =>
          interpolate(fr, [0, 8, 60, 75], [0.7, 0.9, 0.6, 0], { extrapolateRight: "clamp" })} />
      </Sequence>
    </AbsoluteFill>
  );
};
