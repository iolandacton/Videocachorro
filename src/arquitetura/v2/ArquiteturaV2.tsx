import React from "react";
import "@fontsource/montserrat/300.css";
import "@fontsource/montserrat/400.css";
import "@fontsource/montserrat/500.css";
import "@fontsource/montserrat/600.css";
import {
  AbsoluteFill, Audio, Easing, Img, interpolate, OffthreadVideo, random, Sequence, staticFile,
  useCurrentFrame, useVideoConfig,
} from "remotion";

// V2 (cópia de trabalho de Arquitetura.tsx — a versão aprovada não muda). Única diferença: legendas.\n// Linguagem editorial de arquitetura: imagens sempre em movimento lento, transições por
// máscaras de linha, tipografia Montserrat com hierarquia (legenda suave, palavra-chave,
// pares esquerda/direita, listas progressivas com ✕/✓ desenhados). Tempos do roteiro em s.

type Cena = {
  de: number; ate: number; mov: "pushin" | "pullout" | "lateral" | "parado";
  img?: string; video?: string; inicioVideo?: number; split?: [string, string];
  entrada?: "linha-vertical" | "linha-horizontal" | "dissolve" | "corte" | "split";
  luz?: boolean;
};
type Legenda = { de: number; ate: number; destaque?: string[]; palavras: [string, number][] };
type Chave = { linha1: string; t1: number; linha2?: string; t2?: number; ate: number };
// "lado": cada palavra centrada na sua metade (tela dividida); "diagonal": esquerda em cima, direita embaixo
type Par = { esq: string; tEsq: number; dir: string; tDir: number; ate: number; layout?: "lado" | "diagonal" };
type Lista = { tipo: "x" | "check"; itens: { texto: string; t: number }[]; ate?: number };

export type Roteiro = {
  fps: number;
  duracao: number;
  cenas: Cena[];
  legendas: Legenda[];
  palavrasChave?: Chave[];
  pares?: Par[];
  listas?: Lista[];
};

const FONTE = "Montserrat, sans-serif";
const BRANCO = "#F6F3EE";
const AREIA = "#D8C7AC";
const TRANS = 0.75; // duração das entradas (s)
const suave = Easing.bezier(0.45, 0, 0.2, 1);
const SOMBRA = "0 1px 2px rgba(0,0,0,0.35), 0 2px 14px rgba(0,0,0,0.38)";

const rampa = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave });
const filtro = "contrast(1.04) saturate(0.92) sepia(0.06)";

// ---------- Cenas ----------
const Foto: React.FC<{ src: string; transform: string }> = ({ src, transform }) => (
  <Img src={staticFile(`arq/img/${src}.png`)} style={{ width: "100%", height: "100%",
    objectFit: "cover", transform, filter: filtro }} />
);

const Linha: React.FC<{ vertical: boolean; pos: number }> = ({ vertical, pos }) => (
  <div style={{ position: "absolute", background: AREIA, opacity: 0.9, boxShadow: `0 0 18px ${AREIA}`,
    ...(vertical ? { top: 0, bottom: 0, left: `${pos}%`, width: 3 } : { left: 0, right: 0, top: `${pos}%`, height: 3 }) }} />
);

const CenaView: React.FC<{ c: Cena; t: number; fps: number }> = ({ c, t, fps }) => {
  const fim = c.ate + TRANS;
  if (t < c.de || t > fim) return null;
  const p = interpolate(t, [c.de, fim], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const e = c.entrada && c.entrada !== "corte" ? rampa(t, c.de, c.de + TRANS) : 1;
  let escala = 1.1, x = 0;
  if (c.mov === "pushin") escala = 1.05 + 0.09 * p;
  if (c.mov === "pullout") escala = 1.15 - 0.09 * p;
  if (c.mov === "lateral") { escala = 1.13; x = -3.2 + 6.4 * p; }
  if (c.mov === "parado") escala = 1.02 + 0.02 * p;

  let clip = "none", opacidade = 1, extraX = 0, linha: React.ReactNode = null;
  if (c.entrada === "linha-vertical") {
    clip = `inset(0 ${100 - 100 * e}% 0 0)`;
    extraX = 4 * (1 - e); // a imagem nova desliza junto da máscara (parallax)
    if (e < 1) linha = <Linha vertical pos={100 * e} />;
  } else if (c.entrada === "linha-horizontal") {
    clip = `inset(${100 - 100 * e}% 0 0 0)`;
    if (e < 1) linha = <Linha vertical={false} pos={100 - 100 * e} />;
  } else if (c.entrada === "dissolve") {
    opacidade = e;
    escala += 0.05 * (1 - e);
  }
  const transform = `translateX(${x + extraX}%) scale(${escala})`;

  let conteudo: React.ReactNode;
  if (c.split) {
    // tela dividida: metades entram em sentidos opostos e derivam em parallax
    const meia = (src: string, lado: 0 | 1) => {
      const dy = (lado ? 1 : -1) * 100 * (1 - e);
      const deriva = (lado ? -1 : 1) * 2.5 * p;
      return (
        <div style={{ position: "absolute", top: 0, bottom: 0, width: "50%", left: lado ? "50%" : 0,
          overflow: "hidden", transform: `translateY(${dy}%)` }}>
          <div style={{ position: "absolute", top: 0, bottom: 0, width: 1080, left: -270 }}>
            <Foto src={src} transform={`translateY(${deriva}%) scale(${1.08 + 0.04 * p})`} />
          </div>
        </div>
      );
    };
    conteudo = (
      <>
        {meia(c.split[0], 0)}
        {meia(c.split[1], 1)}
        <div style={{ position: "absolute", top: 0, bottom: 0, left: "50%", width: 2, marginLeft: -1,
          background: AREIA, opacity: 0.85 * e }} />
      </>
    );
  } else if (c.video) {
    conteudo = (
      <Sequence from={Math.round(c.de * fps)} layout="none">
        <OffthreadVideo src={staticFile(c.video)} muted startFrom={Math.round((c.inicioVideo ?? 0) * fps)}
          style={{ width: "100%", height: "100%", objectFit: "cover", transform, filter: filtro }} />
      </Sequence>
    );
  } else {
    conteudo = <Foto src={c.img!} transform={transform} />;
  }
  // varredura de luz sobre a textura (sutil)
  const luz = c.luz ? (
    <AbsoluteFill style={{ mixBlendMode: "soft-light", opacity: 0.55,
      background: `linear-gradient(115deg, rgba(255,255,255,0) ${-30 + 120 * p}%, rgba(255,244,225,0.9) ${-12 + 120 * p}%, rgba(255,255,255,0) ${6 + 120 * p}%)` }} />
  ) : null;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: clip, opacity: opacidade }}>{conteudo}{luz}</AbsoluteFill>
      {linha}
    </AbsoluteFill>
  );
};

// ---------- Legenda v2: blocos curtos (2–5 palavras), centralizados, sem cobrir rostos ----------
// Fica na faixa central-baixa (≈52% da altura): abaixo dos rostos nos takes e no gancho.
const LegendaView: React.FC<{ l: Legenda; t: number }> = ({ l, t }) => {
  if (t < l.de - 0.05 || t > l.ate + 0.05) return null;
  const entra = rampa(t, l.de, l.de + 0.22);
  const sai = 1 - rampa(t, l.ate - 0.16, l.ate);
  const dest = (l.destaque ?? []).map((d) => d.toLowerCase());
  return (
    <AbsoluteFill style={{ alignItems: "center", pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: 1000, width: 860, textAlign: "center", fontFamily: FONTE,
        fontWeight: 400, fontSize: 48, lineHeight: 1.3, color: BRANCO, opacity: entra * sai,
        transform: `translateY(${10 * (1 - entra)}px)`, letterSpacing: `${0.03 - 0.018 * entra}em`,
        textShadow: "0 1px 2px rgba(0,0,0,0.35), 0 2px 18px rgba(0,0,0,0.38)" }}>
        {/* halo escuro e difuso atrás do texto: legível sobre fundos claros sem "caixa" */}
        <div style={{ position: "absolute", inset: "-40px -70px", zIndex: -1, borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.30) 0%, rgba(0,0,0,0) 70%)" }} />
        {l.palavras.map(([w], i) => {
          const d = dest.includes(w.toLowerCase().replace(/[.,?!]/g, ""));
          return <span key={i} style={{ color: d ? AREIA : BRANCO, fontWeight: d ? 500 : 400 }}>{w}{" "}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Palavra-chave ----------
const Mascara: React.FC<{ e: number; children: React.ReactNode }> = ({ e, children }) => (
  <div style={{ overflow: "hidden" }}>
    <div style={{ transform: `translateY(${105 * (1 - e)}%)` }}>{children}</div>
  </div>
);

const ChaveView: React.FC<{ k: Chave; t: number }> = ({ k, t }) => {
  if (t < k.t1 - 0.1 || t > k.ate + 0.5) return null;
  const e1 = rampa(t, k.t1, k.t1 + 0.55);
  const e2 = k.t2 !== undefined ? rampa(t, k.t2, k.t2 + 0.45) : 0;
  const sai = rampa(t, k.ate, k.ate + 0.45);
  const linhas2 = (k.linha2 ?? "").split("\n");
  const maior = Math.max(...linhas2.map((s) => s.length), 1);
  const fs1 = Math.min(60, 940 / (k.linha1.length * 1.02));
  const fs2 = Math.min(168, 1090 / maior);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONTE,
      color: BRANCO, opacity: 1 - sai, transform: `translateY(${-24 * sai}px)`, textShadow: SOMBRA }}>
      <div style={{ textAlign: "center", marginTop: -160 }}>
        <Mascara e={e1}><div style={{ fontWeight: 300, fontSize: fs1,
          letterSpacing: `${0.62 - 0.28 * e1}em`, paddingLeft: "0.34em" }}>{k.linha1}</div></Mascara>
        {k.linha2 && <div style={{ height: 2, background: AREIA, margin: "26px auto", width: 260 * e2 }} />}
        {linhas2.map((s, i) => k.linha2 && (
          <Mascara key={i} e={e2}><div style={{ fontWeight: 600, fontSize: fs2, lineHeight: 1.05,
            letterSpacing: `${0.2 - 0.06 * e2}em`, paddingLeft: "0.14em" }}>{s}</div></Mascara>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Par de palavras: uma à esquerda, outra à direita ----------
const ParView: React.FC<{ p: Par; t: number }> = ({ p, t }) => {
  if (t < p.tEsq - 0.1 || t > p.ate + 0.5) return null;
  const sai = rampa(t, p.ate, p.ate + 0.45);
  const diagonal = p.layout === "diagonal";
  const lado = (texto: string, ts: number, direita: boolean) => {
    const e = rampa(t, ts, ts + 0.55);
    const pos: React.CSSProperties = diagonal
      ? { top: direita ? 1040 : 700, left: 84, right: 84, textAlign: direita ? "right" : "left" }
      : { top: 860, width: "50%", left: direita ? "50%" : 0, textAlign: "center" };
    const fs = diagonal ? Math.min(84, 880 / texto.length) : Math.min(70, 470 / (texto.length * 0.95));
    return (
      <div style={{ position: "absolute", opacity: e, ...pos }}>
        <Mascara e={e}><div style={{ fontWeight: 400, fontSize: fs,
          letterSpacing: `${0.42 - 0.14 * e}em`, paddingLeft: diagonal ? 0 : "0.28em" }}>{texto.toUpperCase()}</div></Mascara>
        <div style={{ height: 2, background: AREIA, marginTop: 18, width: 120 * e,
          marginLeft: diagonal && direita ? "auto" : diagonal ? 0 : "auto", marginRight: diagonal && !direita ? 0 : "auto" }} />
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ fontFamily: FONTE, color: BRANCO, opacity: 1 - sai, textShadow: SOMBRA }}>
      {lado(p.esq, p.tEsq, false)}
      {lado(p.dir, p.tDir, true)}
    </AbsoluteFill>
  );
};

// ---------- Lista progressiva com ícones desenhados ----------
const Icone: React.FC<{ tipo: "x" | "check"; e: number }> = ({ tipo, e }) => {
  const a = interpolate(e, [0, 0.5], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const b = interpolate(e, [0.4, 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const traço = { fill: "none", stroke: AREIA, strokeWidth: 2, strokeLinecap: "round" as const };
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

const ListaView: React.FC<{ l: Lista; t: number }> = ({ l, t }) => {
  const visiveis = l.itens.filter((i) => t >= i.t - 0.05);
  if (!visiveis.length || (l.ate !== undefined && t > l.ate + 0.5)) return null;
  const sai = l.ate !== undefined ? rampa(t, l.ate, l.ate + 0.45) : 0;
  const ultimo = visiveis[visiveis.length - 1];
  return (
    <div style={{ position: "absolute", left: 78, top: 250, fontFamily: FONTE, opacity: 1 - sai }}>
      {visiveis.map((it) => {
        const e = rampa(t, it.t, it.t + 0.45);
        // o item novo fica em destaque por ~2,5 s e depois se junta aos demais, discreto
        const foco = it === ultimo ? 1 - rampa(t, it.t + 2.3, it.t + 3.0) : 0;
        const escala = 1 + 0.12 * (1 - rampa(t, it.t + 0.45, it.t + 1.1)) * (it === ultimo ? 1 : 0);
        return (
          <div key={it.texto} style={{ display: "flex", alignItems: "center", height: 72,
            opacity: (0.6 + 0.4 * foco) * e, transform: `translateX(${-22 * (1 - e)}px) scale(${escala})`,
            transformOrigin: "left center" }}>
            <Icone tipo={l.tipo} e={e} />
            <span style={{ fontWeight: foco > 0.5 ? 500 : 400, fontSize: 41, color: BRANCO,
              letterSpacing: "0.015em", textShadow: SOMBRA }}>{it.texto}</span>
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

export const ArquiteturaV2: React.FC<{ roteiro: Roteiro; audio: string }> = ({ roteiro, audio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chaves = roteiro.palavrasChave ?? [];
  const escurece = Math.max(0,
    ...chaves.map((k) => 0.28 * rampa(t, k.t1 - 0.2, k.t1 + 0.3) * (1 - rampa(t, k.ate, k.ate + 0.5))),
    ...(roteiro.pares ?? []).map((p) => 0.3 * rampa(t, p.tEsq - 0.2, p.tEsq + 0.3) * (1 - rampa(t, p.ate, p.ate + 0.5))));
  const fimFade = rampa(t, roteiro.duracao - 0.7, roteiro.duracao);
  return (
    <AbsoluteFill style={{ background: "#111" }}>
      {roteiro.cenas.map((c, i) => <CenaView key={i} c={c} t={t} fps={fps} />)}
      {/* leitura: degradê embaixo e no canto da lista, vinheta suave */}
      <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.32) 34%, rgba(0,0,0,0) 52%)" }} />
      <AbsoluteFill style={{ background: "linear-gradient(165deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.25) 26%, rgba(0,0,0,0) 44%)" }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%)" }} />
      <AbsoluteFill style={{ background: `rgba(0,0,0,${escurece})` }} />
      <Grao frame={frame} />
      {(roteiro.listas ?? []).map((l, i) => <ListaView key={i} l={l} t={t} />)}
      {chaves.map((k, i) => <ChaveView key={i} k={k} t={t} />)}
      {(roteiro.pares ?? []).map((p, i) => <ParView key={i} p={p} t={t} />)}
      {roteiro.legendas.map((l, i) => <LegendaView key={i} l={l} t={t} />)}
      <AbsoluteFill style={{ background: `rgba(0,0,0,${fimFade})` }} />
      <Audio src={staticFile(audio)} />
    </AbsoluteFill>
  );
};
