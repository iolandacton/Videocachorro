import React from "react";
import "@fontsource/montserrat/300-italic.css";
import "@fontsource/montserrat/400.css";
import "@fontsource/montserrat/600.css";
import { AbsoluteFill, Audio, Easing, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Oficina Sete — linguagem da referência: protagonista como base, apoios em dissolve curto, legendas
// minimalistas (minúsculas, Montserrat leve, tarja cinza translúcida no terço inferior) e rótulos de
// detalhe (ícone + linha fina itálica + linha bold). Cor e estabilização já vêm aplicadas nos arquivos.

type Cena = { video: string; inicioVideo: number; de: number; ate: number; entrada?: "dissolve" | "corte" };
type Apoio = Cena & { rotulo?: [string, string]; saida?: "dissolve" | "corte" };
type Legenda = { de: number; ate: number; texto: string };
export type RoteiroOficina = { fps: number; duracao: number; cenas: Cena[]; apoios: Apoio[]; legendas: Legenda[]; fadeFinal: number };

const FONTE = "Montserrat, sans-serif";
const DISSOLVE = 0.35;
const suave = Easing.bezier(0.4, 0, 0.2, 1);
const rampa = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave });

const Video: React.FC<{ c: Cena; ate: number; opacidade: number; fps: number }> = ({ c, ate, opacidade, fps }) => (
  <Sequence from={Math.round(c.de * fps)} durationInFrames={Math.max(1, Math.round((ate - c.de) * fps))} layout="none">
    <AbsoluteFill style={{ opacity: opacidade }}>
      <OffthreadVideo src={staticFile(c.video)} muted startFrom={Math.round(c.inicioVideo * fps)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  </Sequence>
);

const Rotulo: React.FC<{ a: Apoio; t: number }> = ({ a, t }) => {
  if (!a.rotulo) return null;
  const e = rampa(t, a.de + 0.25, a.de + 0.7) * (1 - rampa(t, a.ate - 0.45, a.ate - 0.1));
  if (e <= 0) return null;
  const sombra = "0 1px 2px rgba(0,0,0,0.35), 0 2px 12px rgba(0,0,0,0.30)";
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONTE, color: "#FBFAF8",
      opacity: e, transform: `translateY(${8 * (1 - e)}px)`, textShadow: sombra }}>
      <div style={{ textAlign: "center", marginTop: -40 }}>
        <div style={{ width: 34, height: 34, border: "2px solid rgba(251,250,248,0.9)", borderRadius: 7,
          margin: "0 auto 18px", boxShadow: "0 1px 6px rgba(0,0,0,0.25)" }} />
        <div style={{ fontWeight: 300, fontStyle: "italic", fontSize: 38, letterSpacing: "0.06em", lineHeight: 1.05 }}>{a.rotulo[0]}</div>
        <div style={{ fontWeight: 600, fontSize: 38, letterSpacing: "0.06em", lineHeight: 1.1 }}>{a.rotulo[1]}</div>
      </div>
    </AbsoluteFill>
  );
};

const LegendaView: React.FC<{ l: Legenda; t: number }> = ({ l, t }) => {
  const e = rampa(t, l.de, l.de + 0.15) * (1 - rampa(t, l.ate - 0.12, l.ate));
  if (e <= 0) return null;
  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <div style={{ position: "absolute", top: 1452, maxWidth: 860, fontFamily: FONTE, fontWeight: 400, fontSize: 35,
        lineHeight: 1.3, color: "#F8F6F3", textAlign: "center", padding: "7px 18px",
        background: "rgba(96,96,96,0.46)", opacity: e, transform: `translateY(${4 * (1 - e)}px)` }}>
        {l.texto}
      </div>
    </AbsoluteFill>
  );
};

export const Oficina: React.FC<{ roteiro: RoteiroOficina; audio: string }> = ({ roteiro, audio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cenas = roteiro.cenas;
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {cenas.map((c, i) => {
        const prox = cenas[i + 1];
        const ate = prox ? prox.de + (prox.entrada === "dissolve" ? DISSOLVE : 0) : roteiro.duracao;
        const op = c.entrada === "dissolve" ? rampa(t, c.de, c.de + DISSOLVE) : 1;
        return <Video key={i} c={c} ate={ate} opacidade={op} fps={fps} />;
      })}
      {roteiro.apoios.map((a, i) => {
        const op = rampa(t, a.de, a.de + 0.3) * (a.saida === "corte" ? 1 : 1 - rampa(t, a.ate - 0.28, a.ate));
        return <Video key={`a${i}`} c={a} ate={a.ate} opacidade={op} fps={fps} />;
      })}
      {roteiro.apoios.map((a, i) => <Rotulo key={`r${i}`} a={a} t={t} />)}
      {roteiro.legendas.map((l, i) => <LegendaView key={i} l={l} t={t} />)}
      <AbsoluteFill style={{ background: "#fff", opacity: rampa(t, roteiro.duracao - roteiro.fadeFinal, roteiro.duracao) }} />
      <Audio src={staticFile(audio)} />
    </AbsoluteFill>
  );
};
