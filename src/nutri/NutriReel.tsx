import React from "react";
import {
  AbsoluteFill, Audio, Easing, OffthreadVideo, Sequence, interpolate, spring,
  staticFile, useCurrentFrame,
} from "remotion";
import { loadFont } from "@remotion/fonts";
import raw from "./reel.json";

// Reel completo do nutricionista. Linha do tempo (cortes, legendas, eventos) em reel.json,
// gerada por scripts/nutri/build.py. Legendas no espaço livre acima dele, SEM barra preta.

loadFont({ family: "Poppins", url: staticFile("nutri/fonts/poppins-latin-800-normal.woff2"), weight: "800" });
loadFont({ family: "Poppins", url: staticFile("nutri/fonts/poppins-latin-900-normal.woff2"), weight: "900" });
loadFont({ family: "Playfair", url: staticFile("nutri/fonts/playfair-display-latin-800-italic.woff2"), weight: "800", style: "italic" });

type Kind = "normal" | "key" | "keyPink" | "keyRed" | "alert" | "num" | "quote";
type W = { t: number; text: string; kind: Kind; strikeAt?: number };
type Group = { type: "pop" | "type"; start: number; end: number; lines: W[][] };
type Triple = [number, number, number];
type Data = {
  fps: number; totalFrames: number; voiceEnd: number;
  segs: { file: string; from: number; frames: number }[];
  zooms: Triple[]; groups: Group[];
  ev: {
    cutIn: number; cutOut: number; estradiol: number; tension: [number, number];
    shakes: [number, number][]; redFlashes: Triple[]; redEdges: Triple[]; whiteFlashes: Triple[];
    goldSweep: number; endCard: number;
    sfx: { whoosh: number[]; pop: number[]; impact: [number, number][]; stamp: number[]; riser: number; typing: [number, number] };
  };
};
const D = raw as unknown as Data;
const FPS = D.fps;
export const NUTRI_REEL_FRAMES = D.totalFrames;

const GOLD = "#F6C445", RED = "#FF3B30", PINK = "#FF3D7F", ORANGE = "#FF9F1A";
const SHADOW = "0 4px 22px rgba(0,0,0,0.75), 0 0 6px rgba(0,0,0,0.7), 0 2px 2px rgba(0,0,0,0.6)";
const F = (t: number) => Math.round(t * FPS);
const ALL_T = D.groups.flatMap((g) => g.lines.flat().map((w) => w.t)).sort((a, b) => a - b);
const nextT = (t: number) => Math.min(ALL_T.find((x) => x > t) ?? t + 0.6, t + 0.9);

const zoomAt = (s: number) => {
  let i = 0;
  for (let k = 0; k < D.zooms.length; k++) if (s >= D.zooms[k][0]) i = k;
  const [t0, z0, z1] = D.zooms[i];
  const t1 = D.zooms[i + 1]?.[0] ?? D.totalFrames / FPS;
  const punch = interpolate(s - t0, [0, 0.2], [0.05, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return interpolate(s, [t0, Math.max(t1, t0 + 0.01)], [z0, z1], { extrapolateRight: "clamp" }) + punch;
};
const shakeOne = (s: number, at: number, amp: number) => {
  const d = s - at;
  if (d < 0 || d > 0.4) return { x: 0, y: 0 };
  const k = amp * Math.exp(-d * 9);
  return { x: k * Math.sin(d * 95), y: k * Math.cos(d * 80) };
};
const pulseSum = (s: number, list: Triple[]) =>
  list.reduce((a, [at, dur, peak]) => a + (s >= at
    ? interpolate(s - at, [0, dur], [peak, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.quad) }) : 0), 0);

// ---------- palavra com efeito ----------
const Word: React.FC<{ w: W }> = ({ w }) => {
  const frame = useCurrentFrame();
  const s = frame / FPS;
  const hidden = s < w.t;
  const pop = spring({ frame: frame - w.t * FPS, fps: FPS, config: { damping: 9, stiffness: 190, mass: 0.6 } });
  const active = s < nextT(w.t);
  const age = Math.max(0, s - w.t);
  const base: React.CSSProperties = {
    display: "inline-block", margin: "0 12px", textShadow: SHADOW, position: "relative",
    transform: `scale(${interpolate(pop, [0, 1], [0.4, 1])})`, opacity: hidden ? 0 : Math.min(1, pop * 2),
  };
  let style: React.CSSProperties;
  if (w.kind === "normal") {
    style = { ...base, fontFamily: "Poppins", fontWeight: 800, fontSize: 66, color: active ? GOLD : "white" };
  } else if (w.kind === "quote") {
    style = { ...base, fontFamily: "Playfair", fontStyle: "italic", fontWeight: 800, fontSize: 80, lineHeight: 1.1, color: active ? GOLD : "white" };
  } else if (w.kind === "alert" || w.kind === "num") {
    const sh = shakeOne(s, w.t, 16);
    const color = w.kind === "alert" ? RED : w.text.startsWith("200") ? GOLD : w.text.startsWith("100") ? ORANGE : RED;
    style = { ...base, fontFamily: "Poppins", fontWeight: 900, fontSize: w.kind === "num" ? 236 : 168, lineHeight: 1, color,
      textShadow: `${SHADOW}, 0 0 44px ${color}aa`,
      transform: `translate(${sh.x}px, ${sh.y}px) scale(${interpolate(pop, [0, 1], [2.3, 1])})` };
  } else {
    const color = w.kind === "keyPink" ? PINK : w.kind === "keyRed" ? RED : GOLD;
    const sh = w.kind === "keyRed" ? shakeOne(s, w.t, 10) : { x: 0, y: 0 };
    const pulse = 1 + 0.035 * Math.sin(age * 9) * Math.exp(-age * 1.5);
    style = { ...base, fontFamily: "Playfair", fontStyle: "italic", fontWeight: 800, fontSize: 98, lineHeight: 1.08, color,
      textShadow: `${SHADOW}, 0 0 34px ${color}88`,
      transform: `translate(${sh.x}px, ${sh.y}px) scale(${interpolate(pop, [0, 1], [0.4, 1]) * pulse})` };
  }
  const strike = w.strikeAt !== undefined && s >= w.strikeAt
    ? interpolate(s - w.strikeAt, [0, 0.14], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }) : 0;
  return (
    <span style={style}>
      {w.text}
      {strike > 0 && <span style={{
        position: "absolute", left: "-4%", top: "50%", height: 16, width: `${108 * strike}%`, background: RED, borderRadius: 8,
        transform: "rotate(-7deg)", transformOrigin: "0 50%", boxShadow: "0 0 24px rgba(255,59,48,0.8), 0 3px 10px rgba(0,0,0,0.6)",
      }} />}
    </span>
  );
};

// ---------- gancho digitado (como na referência) ----------
const TypedGroup: React.FC<{ g: Group }> = ({ g }) => {
  const s = useCurrentFrame() / FPS;
  const lines = g.lines.map((line) => {
    const text = line.map((w) => w.text).join(" ");
    let shown = 0;
    line.forEach((w, i) => {
      const len = w.text.length + (i < line.length - 1 ? 1 : 0);
      const dur = Math.min(nextT(w.t) - w.t, 0.42);
      if (s >= w.t) shown += Math.min(len, Math.ceil((len * (s - w.t)) / dur));
    });
    return { text, shown, key: line[0].kind !== "normal", started: s >= line[0].t };
  });
  let cur = 0;
  lines.forEach((l, i) => { if (l.started) cur = i; });
  return (
    <>
      {lines.map((l, i) => {
        const style: React.CSSProperties = l.key
          ? { fontFamily: "Playfair", fontStyle: "italic", fontWeight: 800, fontSize: 104, lineHeight: 1.1, color: GOLD, textShadow: `${SHADOW}, 0 0 34px ${GOLD}88` }
          : { fontFamily: "Poppins", fontWeight: 800, fontSize: 60, lineHeight: 1.22, color: "white", textShadow: SHADOW };
        const blink = Math.floor(s * 5) % 2 === 0 || l.shown < l.text.length;
        return (
          <div key={i} style={{ ...style, whiteSpace: "pre" }}>
            <span>{l.text.slice(0, l.shown)}</span>
            <span style={{ display: "inline-block", width: 0, overflow: "visible", opacity: i === cur && blink ? 1 : 0, color: "white", fontFamily: "Poppins", fontStyle: "normal" }}>▍</span>
            <span style={{ opacity: 0 }}>{l.text.slice(l.shown)}</span>
          </div>
        );
      })}
    </>
  );
};

const Captions: React.FC = () => {
  const s = useCurrentFrame() / FPS;
  const g = D.groups.find((x) => s >= x.start - 0.02 && s < x.end);
  if (!g) return null;
  const out = interpolate(s, [g.end - 0.08, g.end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", top: 225, left: 46, right: 46, height: 370, opacity: out,
      display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", gap: 4,
    }}>
      {g.type === "type" ? <TypedGroup g={g} /> : g.lines.map((line, i) => (
        <div key={i} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline" }}>
          {line.map((w) => <Word key={w.t} w={w} />)}
        </div>
      ))}
    </div>
  );
};

// ---------- cartão final ----------
const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const s = frame / FPS - D.ev.endCard;
  if (s < 0) return null;
  const a = interpolate(s, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const p = (delay: number) => spring({ frame: frame - (D.ev.endCard + delay) * FPS, fps: FPS, config: { damping: 11, stiffness: 170, mass: 0.7 } });
  const pulse = 1 + 0.06 * Math.sin(s * 9);
  return (
    <AbsoluteFill style={{ opacity: a }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0.86) 100%)", backdropFilter: "blur(10px)" }} />
      <div style={{ position: "absolute", top: 560, left: 60, right: 60, textAlign: "center" }}>
        <div style={{ fontFamily: "Poppins", fontWeight: 800, fontSize: 58, color: "white", textShadow: SHADOW, transform: `scale(${p(0.05)})` }}>Agende seu</div>
        <div style={{ fontFamily: "Playfair", fontStyle: "italic", fontWeight: 800, fontSize: 104, lineHeight: 1.08, color: GOLD,
          textShadow: `${SHADOW}, 0 0 40px ${GOLD}88`, transform: `scale(${p(0.18)})`, marginTop: 10 }}>acompanhamento<br />nutricional</div>
        <div style={{ margin: "56px auto 0", width: interpolate(p(0.4), [0, 1], [0, 420]), height: 6, borderRadius: 3, background: GOLD, boxShadow: `0 0 22px ${GOLD}` }} />
        <div style={{ marginTop: 44, fontFamily: "Poppins", fontWeight: 800, fontSize: 54, color: "white", textShadow: SHADOW,
          transform: `scale(${p(0.5) * pulse})` }}><span style={{ color: GOLD }}>➜ </span>@paulogabrielnutri</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- composição ----------
export const NutriReel: React.FC = () => {
  const frame = useCurrentFrame();
  const s = frame / FPS;
  const { ev } = D;
  const cutInF = F(ev.cutIn), cutOutF = F(ev.cutOut);
  const inCut = frame >= cutInF && frame < cutOutF;

  const shake = ev.shakes.reduce((a, [at, amp]) => { const k = shakeOne(s, at, amp); return { x: a.x + k.x, y: a.y + k.y }; }, { x: 0, y: 0 });
  const tension = interpolate(s, ev.tension, [0, 0.62], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const white = pulseSum(s, ev.whiteFlashes), red = pulseSum(s, ev.redFlashes), redEdge = pulseSum(s, ev.redEdges);
  const eIn = spring({ frame: frame - ev.estradiol * FPS, fps: FPS, config: { damping: 11, stiffness: 220, mass: 0.7 } });
  const eSh = shakeOne(s, ev.estradiol, 30);
  const sweep = interpolate(s - ev.goldSweep, [0, 0.7], [-60, 160], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const total = D.totalFrames / FPS;
  const E = ev.estradiol, VE = D.voiceEnd;
  const musicVol = (f: number) => interpolate(f / FPS,
    [0, 0.1, 0.9, E - 1.5, E - 0.9, E - 0.03, E, E + 0.7, E + 1.3, VE - 0.2, VE + 0.4, total - 0.4, total],
    [0, 0.32, 0.17, 0.17, 0.03, 0.03, 0.3, 0.3, 0.17, 0.17, 0.42, 0.42, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ transform: `translate(${shake.x}px, ${shake.y}px)` }}>
        <AbsoluteFill style={{ transform: `scale(${zoomAt(s)})`, transformOrigin: "50% 33%", filter: "contrast(1.04) saturate(1.05)" }}>
          {D.segs.map((sg) => (
            <Sequence key={sg.file} from={sg.from} durationInFrames={sg.frames}>
              <OffthreadVideo muted src={staticFile(sg.file)} style={{ width: "100%", height: "100%" }} />
            </Sequence>
          ))}
        </AbsoluteFill>
        {/* animação do Runway: moléculas douradas → rosa, virada em "estradiol" */}
        <Sequence from={cutInF} durationInFrames={cutOutF - cutInF}>
          <AbsoluteFill style={{ transform: `scale(${interpolate(s, [ev.cutIn, ev.cutOut], [1.3, 1.5])})`, transformOrigin: "50% 47%" }}>
            <OffthreadVideo muted src={staticFile("nutri/moleculas.mp4")} playbackRate={1.06} startFrom={F(0.99)} style={{ width: "100%", height: "100%" }} />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>

      {/* escurecimento suave atrás das legendas (sem barra) */}
      {!inCut && <AbsoluteFill style={{
        background: `radial-gradient(ellipse 88% 34% at 50% 20%, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0.22) 55%, rgba(0,0,0,0) 100%)`,
      }} />}
      {!inCut && tension > 0 && <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 38%, rgba(0,0,0,${tension}) 100%)` }} />}
      <AbsoluteFill style={{ boxShadow: `inset 0 0 220px 40px rgba(255,40,30,${Math.min(1, redEdge)})` }} />

      <Captions />

      {s >= ev.estradiol && frame < cutOutF && (
        <div style={{
          position: "absolute", left: 0, right: 0, top: 1235, textAlign: "center",
          fontFamily: "Poppins", fontWeight: 900, fontSize: 158, letterSpacing: 2, color: "white",
          textShadow: `0 0 18px ${PINK}, 0 0 60px ${PINK}, 0 0 120px rgba(255,61,127,0.8), 0 6px 26px rgba(0,0,0,0.8), -5px 0 0 rgba(255,40,60,0.75), 5px 0 0 rgba(60,200,255,0.55)`,
          transform: `translate(${eSh.x}px, ${eSh.y}px) scale(${interpolate(eIn, [0, 1], [3.2, 1])})`, opacity: Math.min(1, eIn * 3),
        }}>ESTRADIOL</div>
      )}

      {/* brilho dourado na chamada final */}
      {s >= ev.goldSweep && s < ev.goldSweep + 0.7 && <AbsoluteFill style={{
        background: `linear-gradient(115deg, rgba(246,196,69,0) ${sweep - 22}%, rgba(255,226,140,0.5) ${sweep}%, rgba(246,196,69,0) ${sweep + 22}%)`, mixBlendMode: "screen",
      }} />}

      <EndCard />
      <AbsoluteFill style={{ backgroundColor: "white", opacity: Math.min(1, white) }} />
      <AbsoluteFill style={{ backgroundColor: "#ff1f1f", opacity: Math.min(1, red), mixBlendMode: "screen" }} />

      {/* som */}
      <Audio src={staticFile("nutri/full/voz.wav")} />
      <Audio src={staticFile("nutri/full/musica.wav")} volume={musicVol} />
      <Sequence from={F(ev.sfx.typing[0])} durationInFrames={F(ev.sfx.typing[1] - ev.sfx.typing[0])}>
        <Audio src={staticFile("nutri/sfx/digitacao.wav")} volume={0.32} />
      </Sequence>
      {ev.sfx.whoosh.map((t) => <Sequence key={`w${t}`} from={Math.max(0, F(t) - 5)}><Audio src={staticFile("nutri/sfx/whoosh.wav")} volume={0.42} /></Sequence>)}
      {ev.sfx.pop.map((t) => <Sequence key={`p${t}`} from={F(t)}><Audio src={staticFile("nutri/sfx/pop.wav")} volume={0.45} /></Sequence>)}
      {ev.sfx.impact.map(([t, v]) => <Sequence key={`i${t}`} from={F(t)}><Audio src={staticFile("nutri/sfx/impacto.wav")} volume={v} /></Sequence>)}
      {ev.sfx.stamp.map((t) => <Sequence key={`s${t}`} from={F(t)}><Audio src={staticFile("nutri/sfx/carimbo.wav")} volume={0.6} /></Sequence>)}
      <Sequence from={F(ev.sfx.riser)} durationInFrames={5 * FPS}><Audio src={staticFile("nutri/sfx/subida.wav")} volume={0.5} /></Sequence>
    </AbsoluteFill>
  );
};
