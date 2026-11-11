import React from "react";
import {
  AbsoluteFill, Audio, Easing, OffthreadVideo, Sequence, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/fonts";

// Reel do nutricionista — PRÉVIA de 15 s (trecho da revelação, clipe C6496 de 1,40 a 16,40 s).
// Legendas com efeito no espaço livre acima dele, SEM barra/caixa preta.
// Textos = exatamente o que ele fala (transcrição conferida). Tempos em segundos da prévia.

loadFont({ family: "Poppins", url: staticFile("nutri/fonts/poppins-latin-800-normal.woff2"), weight: "800" });
loadFont({ family: "Poppins", url: staticFile("nutri/fonts/poppins-latin-900-normal.woff2"), weight: "900" });
loadFont({ family: "Playfair", url: staticFile("nutri/fonts/playfair-display-latin-800-italic.woff2"), weight: "800", style: "italic" });

const FPS = 30;
const GOLD = "#F6C445";
const RED = "#FF3B30";
const PINK = "#FF3D7F";
const SHADOW = "0 4px 22px rgba(0,0,0,0.75), 0 0 6px rgba(0,0,0,0.7), 0 2px 2px rgba(0,0,0,0.6)";

// ---------- roteiro de legendas ----------
type Kind = "normal" | "key" | "alert" | "keyPink";
type W = { t: number; text: string; kind?: Kind; strikeAt?: number };
type Group = { start: number; end: number; lines: W[][] };

const GROUPS: Group[] = [
  { start: 0.16, end: 1.72, lines: [[{ t: 0.16, text: "E" }, { t: 0.74, text: "nesses" }, { t: 1.0, text: "casos," }]] },
  { start: 1.78, end: 3.52, lines: [
    [{ t: 1.78, text: "mesmo" }, { t: 1.9, text: "fazendo" }, { t: 2.24, text: "a" }],
    [{ t: 2.38, text: "reposição", kind: "key" }, { t: 2.84, text: "hormonal,", kind: "key" }],
  ] },
  { start: 3.6, end: 4.6, lines: [[{ t: 3.6, text: "essa" }, { t: 4.14, text: "reposição" }]] },
  { start: 4.64, end: 5.56, lines: [
    [{ t: 4.64, text: "NÃO", kind: "alert" }],
    [{ t: 4.8, text: "vai" }, { t: 4.9, text: "ser" }, { t: 5.02, text: "convertida" }],
  ] },
  { start: 5.6, end: 7.5, lines: [
    [{ t: 5.6, text: "em" }, { t: 5.9, text: "testosterona", kind: "key", strikeAt: 6.25 }],
    [{ t: 6.52, text: "dentro" }, { t: 6.9, text: "do" }, { t: 7.06, text: "corpo," }],
  ] },
  { start: 7.7, end: 8.7, lines: [[{ t: 7.7, text: "justamente" }, { t: 8.1, text: "por" }, { t: 8.38, text: "conta" }, { t: 8.6, text: "do" }]] },
  { start: 8.74, end: 10.38, lines: [
    [{ t: 8.74, text: "acúmulo" }, { t: 9.2, text: "de" }],
    [{ t: 9.3, text: "gordura", kind: "key" }, { t: 9.62, text: "corporal,", kind: "key" }],
  ] },
  { start: 10.44, end: 11.28, lines: [[{ t: 10.44, text: "essa" }, { t: 10.64, text: "testosterona", kind: "key" }]] },
  { start: 11.32, end: 12.66, lines: [[{ t: 11.32, text: "vai" }, { t: 11.46, text: "ser" }, { t: 11.58, text: "convertida" }, { t: 12.22, text: "em" }]] },
  { start: 13.78, end: 15.0, lines: [
    [{ t: 13.78, text: "um" }],
    [{ t: 14.0, text: "hormônio", kind: "keyPink" }, { t: 14.28, text: "feminino", kind: "keyPink" }],
  ] },
];
const ALL_T = GROUPS.flatMap((g) => g.lines.flat().map((w) => w.t)).sort((a, b) => a - b);
const nextT = (t: number) => ALL_T.find((x) => x > t) ?? t + 0.6;

// ---------- momentos-chave ----------
const CUTAWAY_IN = 10.44, CUTAWAY_OUT = 13.75, ESTRADIOL = 12.7, NAO = 4.64;
const CUT_IN_F = Math.round(CUTAWAY_IN * FPS), CUT_OUT_F = Math.round(CUTAWAY_OUT * FPS);
const MOL_OFFSET = 0.99; // a virada dourado→rosa do clipe (3,25 s) cai em "estradiol"

// zoom com cortes secos (cada item: início, zoom inicial → zoom final até o próximo)
const ZOOMS: [number, number, number][] = [
  [0, 1.0, 1.06], [1.78, 1.26, 1.31], [3.6, 1.08, 1.12], [NAO, 1.48, 1.55],
  [6.52, 1.0, 1.04], [7.7, 1.04, 1.4], [CUTAWAY_OUT, 1.52, 1.62],
];
const zoomAt = (s: number) => {
  let i = 0;
  for (let k = 0; k < ZOOMS.length; k++) if (s >= ZOOMS[k][0]) i = k;
  const [t0, z0, z1] = ZOOMS[i];
  const t1 = ZOOMS[i + 1]?.[0] ?? 15;
  // assentamento rápido logo após o corte (soco de câmera)
  const punch = interpolate(s - t0, [0, 0.2], [0.05, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return interpolate(s, [t0, t1], [z0, z1], { extrapolateRight: "clamp" }) + punch;
};
const shakeAt = (s: number, at: number, amp: number) => {
  const d = s - at;
  if (d < 0 || d > 0.4) return { x: 0, y: 0 };
  const k = amp * Math.exp(-d * 9);
  return { x: k * Math.sin(d * 95), y: k * Math.cos(d * 80) };
};

// ---------- palavra animada ----------
const Word: React.FC<{ w: W }> = ({ w }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = frame / fps;
  const hidden = s < w.t; // reserva o espaço: a linha não "anda" quando a palavra entra
  const kind = w.kind ?? "normal";
  const pop = spring({ frame: frame - w.t * fps, fps, config: { damping: 9, stiffness: 190, mass: 0.6 } });
  const active = s < nextT(w.t);
  const base: React.CSSProperties = {
    display: "inline-block", margin: "0 12px", textShadow: SHADOW,
    transform: `scale(${interpolate(pop, [0, 1], [0.4, 1])})`, opacity: Math.min(1, pop * 2),
  };
  let style: React.CSSProperties;
  if (kind === "normal") {
    style = { ...base, fontFamily: "Poppins", fontWeight: 800, fontSize: 66, color: active ? GOLD : "white" };
  } else if (kind === "alert") {
    const sh = shakeAt(s, w.t, 16);
    style = { ...base, fontFamily: "Poppins", fontWeight: 900, fontSize: 168, lineHeight: 1, color: RED,
      textShadow: `${SHADOW}, 0 0 40px rgba(255,59,48,0.65)`,
      transform: `translate(${sh.x}px, ${sh.y}px) scale(${interpolate(pop, [0, 1], [2.2, 1])})` };
  } else {
    const color = kind === "keyPink" ? PINK : GOLD;
    const glow = kind === "keyPink" ? "rgba(255,61,127,0.55)" : "rgba(246,196,69,0.5)";
    const pulse = 1 + 0.035 * Math.sin((s - w.t) * 9) * Math.exp(-(s - w.t) * 1.5);
    style = { ...base, fontFamily: "Playfair", fontStyle: "italic", fontWeight: 800, fontSize: 98, lineHeight: 1.08,
      color, textShadow: `${SHADOW}, 0 0 34px ${glow}`,
      transform: `scale(${interpolate(pop, [0, 1], [0.4, 1]) * pulse})` };
  }
  const strike = w.strikeAt !== undefined && s >= w.strikeAt
    ? interpolate(s - w.strikeAt, [0, 0.14], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) })
    : 0;
  return (
    <span style={{ ...style, position: "relative", ...(hidden ? { opacity: 0 } : {}) }}>
      {w.text}
      {strike > 0 && (
        <span style={{
          position: "absolute", left: "-4%", top: "50%", height: 16, width: `${108 * strike}%`,
          background: RED, borderRadius: 8, transform: "rotate(-7deg)", transformOrigin: "0 50%",
          boxShadow: "0 0 24px rgba(255,59,48,0.8), 0 3px 10px rgba(0,0,0,0.6)",
        }} />
      )}
    </span>
  );
};

const Captions: React.FC = () => {
  const s = useCurrentFrame() / FPS;
  const g = GROUPS.find((x) => s >= x.start && s < x.end);
  if (!g) return null;
  const out = interpolate(s, [g.end - 0.08, g.end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", top: 235, left: 50, right: 50, height: 350, opacity: out,
      display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", gap: 6,
    }}>
      {g.lines.map((line, i) => (
        <div key={i} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline" }}>
          {line.map((w) => <Word key={w.t} w={w} />)}
        </div>
      ))}
    </div>
  );
};

// ---------- composição ----------
export const NUTRI_PREVIA_FRAMES = 15 * FPS;

export const NutriPrevia: React.FC = () => {
  const frame = useCurrentFrame();
  const s = frame / FPS;
  const inCut = frame >= CUT_IN_F && frame < CUT_OUT_F;

  const sh1 = shakeAt(s, NAO, 14), sh2 = shakeAt(s, ESTRADIOL, 22), sh3 = shakeAt(s, CUTAWAY_OUT, 10);
  const shake = { x: sh1.x + sh2.x + sh3.x, y: sh1.y + sh2.y + sh3.y };
  // tensão antes da revelação: bordas escurecem
  const tension = interpolate(s, [7.7, CUTAWAY_IN], [0, 0.62], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const flash = (at: number, dur: number, peak: number) =>
    s >= at ? interpolate(s - at, [0, dur], [peak, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.quad) }) : 0;
  const white = flash(CUTAWAY_IN, 0.16, 0.9) + flash(CUTAWAY_OUT, 0.14, 0.8);
  const red = flash(ESTRADIOL, 0.5, 0.7) + flash(NAO, 0.3, 0.28);
  const redEdge = flash(NAO, 0.7, 0.9);

  // ESTRADIOL: palavra gigante que bate na tela
  const eIn = spring({ frame: frame - ESTRADIOL * FPS, fps: FPS, config: { damping: 11, stiffness: 220, mass: 0.7 } });
  const molZoom = interpolate(s, [CUTAWAY_IN, CUTAWAY_OUT], [1.3, 1.5]);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ transform: `translate(${shake.x}px, ${shake.y}px)` }}>
        {/* ele falando — zoom ancorado acima do rosto para manter o espaço livre no topo */}
        <AbsoluteFill style={{
          transform: `scale(${zoomAt(Math.min(s, inCut ? CUTAWAY_IN - 0.01 : s))})`, transformOrigin: "50% 33%",
          filter: "contrast(1.04) saturate(1.05)",
        }}>
          <OffthreadVideo muted src={staticFile("nutri/c6496_proxy.mp4")} style={{ width: "100%", height: "100%" }} />
        </AbsoluteFill>

        {/* animação gerada no Runway (moléculas douradas → rosa) */}
        <Sequence from={CUT_IN_F} durationInFrames={CUT_OUT_F - CUT_IN_F}>
          <AbsoluteFill style={{ transform: `scale(${molZoom})`, transformOrigin: "50% 47%" }}>
            <OffthreadVideo muted src={staticFile("nutri/moleculas.mp4")} startFrom={Math.round(MOL_OFFSET * FPS)}
              style={{ width: "100%", height: "100%" }} />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>

      {/* escurecimento suave atrás das legendas (sem barra) + tensão nas bordas */}
      {!inCut && <AbsoluteFill style={{
        background: "radial-gradient(ellipse 85% 34% at 50% 20%, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0.22) 55%, rgba(0,0,0,0) 100%)",
      }} />}
      {!inCut && <AbsoluteFill style={{
        background: `radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 38%, rgba(0,0,0,${tension}) 100%)`,
      }} />}
      <AbsoluteFill style={{ boxShadow: `inset 0 0 220px 40px rgba(255,40,30,${redEdge})` }} />

      <Captions />

      {s >= ESTRADIOL && frame < CUT_OUT_F && (
        <div style={{
          position: "absolute", left: 0, right: 0, top: 1235, textAlign: "center",
          fontFamily: "Poppins", fontWeight: 900, fontSize: 158, letterSpacing: 2, color: "white",
          textShadow: `0 0 18px ${PINK}, 0 0 60px ${PINK}, 0 0 120px rgba(255,61,127,0.8), 0 6px 26px rgba(0,0,0,0.8), -5px 0 0 rgba(255,40,60,0.75), 5px 0 0 rgba(60,200,255,0.55)`,
          transform: `translate(${sh2.x * 1.5}px, ${sh2.y * 1.5}px) scale(${interpolate(eIn, [0, 1], [3.2, 1])})`,
          opacity: Math.min(1, eIn * 3),
        }}>
          ESTRADIOL
        </div>
      )}

      <AbsoluteFill style={{ backgroundColor: "white", opacity: Math.min(1, white) }} />
      <AbsoluteFill style={{ backgroundColor: "#ff1f1f", opacity: Math.min(1, red), mixBlendMode: "screen" }} />

      {/* som */}
      <Audio src={staticFile("nutri/c6496_voz.wav")} />
      {[1.78, 3.6, 6.52, CUTAWAY_IN, CUTAWAY_OUT].map((t) => (
        <Sequence key={`w${t}`} from={Math.round(t * FPS) - 5}><Audio src={staticFile("nutri/sfx/whoosh.wav")} volume={0.5} /></Sequence>
      ))}
      {[2.38, 5.9, 9.3, 10.64, 14.0].map((t) => (
        <Sequence key={`p${t}`} from={Math.round(t * FPS)}><Audio src={staticFile("nutri/sfx/pop.wav")} volume={0.5} /></Sequence>
      ))}
      <Sequence from={Math.round(NAO * FPS)}><Audio src={staticFile("nutri/sfx/impacto.wav")} volume={0.6} /></Sequence>
      <Sequence from={Math.round(6.25 * FPS)}><Audio src={staticFile("nutri/sfx/carimbo.wav")} volume={0.6} /></Sequence>
      <Sequence from={Math.round((ESTRADIOL - 5) * FPS)} durationInFrames={5 * FPS}>
        <Audio src={staticFile("nutri/sfx/subida.wav")} volume={0.55} />
      </Sequence>
      <Sequence from={Math.round(ESTRADIOL * FPS)}><Audio src={staticFile("nutri/sfx/impacto.wav")} volume={0.6} /></Sequence>
      <Sequence from={Math.round(CUTAWAY_OUT * FPS)}><Audio src={staticFile("nutri/sfx/impacto.wav")} volume={0.4} /></Sequence>
    </AbsoluteFill>
  );
};
