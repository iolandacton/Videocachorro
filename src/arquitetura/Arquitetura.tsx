import React from "react";
import "@fontsource/montserrat/300.css";
import "@fontsource/montserrat/500.css";
import "@fontsource/montserrat/600.css";
import {
  AbsoluteFill, Audio, Easing, Img, interpolate, random, staticFile, useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Linguagem editorial de arquitetura: imagens sempre em movimento lento, transições por
// máscaras de linha, tipografia Montserrat com hierarquia (legenda discreta, palavra-chave,
// lista progressiva com ✕/✓ desenhados). Tudo sincronizado pelos tempos do roteiro (s).

export type Roteiro = {
  fps: number;
  duracao: number;
  cenas: { img: string; de: number; ate: number; mov: "pushin" | "pullout" | "lateral";
    entrada?: "linha-vertical" | "linha-horizontal" | "dissolve" }[];
  legendas: { de: number; ate: number; destaque?: string; palavras: [string, number][] }[];
  palavraChave?: { linha1: string; t1: number; linha2?: string; t2?: number; ate: number };
  lista?: { tipo: "x" | "check"; itens: { texto: string; t: number }[]; ate?: number };
};

const FONTE = "Montserrat, sans-serif";
const BRANCO = "#F6F3EE";
const AREIA = "#D8C7AC";
const TRANS = 0.75; // duração das entradas (s)
const suave = Easing.bezier(0.45, 0, 0.2, 1);

const rampa = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave });

// ---------- Imagem com movimento de câmera ----------
const Cena: React.FC<{ c: Roteiro["cenas"][number]; t: number }> = ({ c, t }) => {
  const fim = c.ate + TRANS;
  const p = interpolate(t, [c.de, fim], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const e = rampa(t, c.de, c.de + TRANS);
  let escala = 1.1, x = 0;
  if (c.mov === "pushin") escala = 1.05 + 0.09 * p;
  if (c.mov === "pullout") escala = 1.15 - 0.09 * p;
  if (c.mov === "lateral") { escala = 1.13; x = -3.2 + 6.4 * p; }

  let clip = "none", opacidade = 1, extraX = 0, linha: React.ReactNode = null;
  if (c.entrada === "linha-vertical") {
    const w = 100 * e;
    clip = `inset(0 ${100 - w}% 0 0)`;
    extraX = 4 * (1 - e); // a imagem nova desliza junto da máscara (parallax)
    if (e > 0 && e < 1) linha = <div style={{ position: "absolute", top: 0, bottom: 0, left: `${w}%`,
      width: 3, background: AREIA, opacity: 0.9, boxShadow: `0 0 18px ${AREIA}` }} />;
  } else if (c.entrada === "linha-horizontal") {
    const h = 100 * e;
    clip = `inset(${100 - h}% 0 0 0)`;
    if (e > 0 && e < 1) linha = <div style={{ position: "absolute", left: 0, right: 0, top: `${100 - h}%`,
      height: 3, background: AREIA, opacity: 0.9, boxShadow: `0 0 18px ${AREIA}` }} />;
  } else if (c.entrada === "dissolve") {
    opacidade = e;
    escala += 0.05 * (1 - e);
  }
  if (t < c.de || t > fim) return null;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: clip, opacity: opacidade }}>
        <Img src={staticFile(`arq/img/${c.img}.png`)} style={{
          width: "100%", height: "100%", objectFit: "cover",
          transform: `translateX(${x + extraX}%) scale(${escala})`,
          filter: "contrast(1.04) saturate(0.92) sepia(0.06)",
        }} />
      </AbsoluteFill>
      {linha}
    </AbsoluteFill>
  );
};

// ---------- Legenda discreta, palavra a palavra ----------
const Legenda: React.FC<{ l: Roteiro["legendas"][number]; t: number }> = ({ l, t }) => {
  if (t < l.de - 0.1 || t > l.ate + 0.1) return null;
  const sai = 1 - rampa(t, l.ate - 0.3, l.ate);
  return (
    <div style={{ position: "absolute", left: 84, right: 160, top: 1330, fontFamily: FONTE,
      fontWeight: 500, fontSize: 42, lineHeight: 1.35, color: BRANCO, opacity: sai,
      textShadow: "0 2px 14px rgba(0,0,0,0.45)", letterSpacing: "0.01em" }}>
      {l.palavras.map(([w, ts], i) => {
        const e = rampa(t, ts - 0.05, ts + 0.2);
        const dest = l.destaque && w.toLowerCase().startsWith(l.destaque);
        return (
          <span key={i} style={{ display: "inline-block", marginRight: "0.28em", opacity: e,
            transform: `translateY(${10 * (1 - e)}px)`, color: dest ? AREIA : BRANCO,
            fontWeight: dest ? 600 : 500 }}>{w}</span>
        );
      })}
    </div>
  );
};

// ---------- Palavra-chave ----------
const PalavraChave: React.FC<{ k: NonNullable<Roteiro["palavraChave"]>; t: number }> = ({ k, t }) => {
  if (t < k.t1 - 0.1 || t > k.ate + 0.5) return null;
  const e1 = rampa(t, k.t1, k.t1 + 0.55);
  const e2 = k.t2 !== undefined ? rampa(t, k.t2, k.t2 + 0.45) : 0;
  const sai = rampa(t, k.ate, k.ate + 0.45);
  const mascara = (e: number, filho: React.ReactNode) => (
    <div style={{ overflow: "hidden" }}>
      <div style={{ transform: `translateY(${105 * (1 - e)}%)` }}>{filho}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONTE,
      color: BRANCO, opacity: 1 - sai, transform: `translateY(${-24 * sai}px)` }}>
      <div style={{ textAlign: "center", marginTop: -160 }}>
        {mascara(e1, <div style={{ fontWeight: 300, fontSize: 60,
          letterSpacing: `${0.62 - 0.28 * e1}em`, paddingLeft: "0.34em" }}>{k.linha1}</div>)}
        <div style={{ height: 2, background: AREIA, margin: "26px auto", width: 260 * e2 }} />
        {k.linha2 && mascara(e2, <div style={{ fontWeight: 600, fontSize: 168, lineHeight: 1,
          letterSpacing: `${0.2 - 0.06 * e2}em`, paddingLeft: "0.14em" }}>{k.linha2}</div>)}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Lista progressiva com ícones desenhados ----------
const Icone: React.FC<{ tipo: "x" | "check"; e: number }> = ({ tipo, e }) => {
  const a = interpolate(e, [0, 0.5], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const b = interpolate(e, [0.4, 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const traço = { fill: "none", stroke: AREIA, strokeWidth: 2.2, strokeLinecap: "round" as const };
  return (
    <svg width="34" height="34" viewBox="0 0 24 24" style={{ flex: "none", marginRight: 22 }}>
      {tipo === "x" ? (
        <>
          <line x1="5" y1="5" x2="19" y2="19" {...traço} strokeDasharray="20" strokeDashoffset={20 * a} />
          <line x1="19" y1="5" x2="5" y2="19" {...traço} strokeDasharray="20" strokeDashoffset={20 * b} />
        </>
      ) : (
        <polyline points="4,12.5 9.5,18 20,6" {...traço} strokeDasharray="26"
          strokeDashoffset={26 * Math.max(a, b)} />
      )}
    </svg>
  );
};

const Lista: React.FC<{ l: NonNullable<Roteiro["lista"]>; t: number }> = ({ l, t }) => {
  const visiveis = l.itens.filter((i) => t >= i.t - 0.05);
  if (!visiveis.length || (l.ate !== undefined && t > l.ate + 0.5)) return null;
  const sai = l.ate !== undefined ? rampa(t, l.ate, l.ate + 0.45) : 0;
  const ultimo = visiveis[visiveis.length - 1];
  return (
    <div style={{ position: "absolute", left: 78, top: 250, fontFamily: FONTE, opacity: 1 - sai }}>
      {visiveis.map((it) => {
        const e = rampa(t, it.t, it.t + 0.45);
        const atual = it === ultimo;
        const escala = atual ? 1 + 0.12 * (1 - rampa(t, it.t + 0.45, it.t + 1.1)) : 1;
        return (
          <div key={it.texto} style={{ display: "flex", alignItems: "center", height: 72,
            opacity: (atual ? 1 : 0.55) * e, transform: `translateX(${-22 * (1 - e)}px) scale(${escala})`,
            transformOrigin: "left center" }}>
            <Icone tipo={l.tipo} e={e} />
            <span style={{ fontWeight: atual ? 600 : 500, fontSize: 41, color: BRANCO,
              letterSpacing: "0.015em", textShadow: "0 1px 3px rgba(0,0,0,0.55), 0 2px 16px rgba(0,0,0,0.5)" }}>{it.texto}</span>
          </div>
        );
      })}
    </div>
  );
};

// ---------- Grão de filme sutil ----------
const Grao: React.FC<{ frame: number }> = ({ frame }) => (
  <AbsoluteFill style={{ opacity: 0.07, mixBlendMode: "overlay", overflow: "hidden" }}>
    <svg width="1300" height="2200" style={{ position: "absolute",
      transform: `translate(${-110 * random(`gx${frame}`)}px, ${-140 * random(`gy${frame}`)}px)` }}>
      <filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" /></filter>
      <rect width="100%" height="100%" filter="url(#g)" />
    </svg>
  </AbsoluteFill>
);

export const Arquitetura: React.FC<{ roteiro: Roteiro; audio: string }> = ({ roteiro, audio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const k = roteiro.palavraChave;
  const escurece = k ? 0.28 * rampa(t, k.t1 - 0.2, k.t1 + 0.3) * (1 - rampa(t, k.ate, k.ate + 0.5)) : 0;
  return (
    <AbsoluteFill style={{ background: "#111" }}>
      {roteiro.cenas.map((c) => <Cena key={c.img + c.de} c={c} t={t} />)}
      {/* leitura: degradê embaixo e no canto da lista, vinheta suave */}
      <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 38%)" }} />
      <AbsoluteFill style={{ background: "linear-gradient(165deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.25) 26%, rgba(0,0,0,0) 44%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%)" }} />
      <AbsoluteFill style={{ background: `rgba(0,0,0,${escurece})` }} />
      <Grao frame={frame} />
      {roteiro.lista && <Lista l={roteiro.lista} t={t} />}
      {k && <PalavraChave k={k} t={t} />}
      {roteiro.legendas.map((l, i) => <Legenda key={i} l={l} t={t} />)}
      <Audio src={staticFile(audio)} />
    </AbsoluteFill>
  );
};
