import React from "react";
import "@fontsource/montserrat/300-italic.css";
import "@fontsource/montserrat/400.css";
import "@fontsource/montserrat/600.css";
import { CartelaLogo, OutroOficina, OUTRO_DUR } from "./OutroOficina";
import { AbsoluteFill, Audio, Easing, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Oficina Sete — linguagem da referência: protagonista como base, apoios em dissolve curto, legendas
// minimalistas (minúsculas, Montserrat leve, tarja cinza translúcida no terço inferior) e rótulos de
// detalhe (ícone + linha fina itálica + linha bold). Cor e estabilização já vêm aplicadas nos arquivos.

type Cena = { video: string; inicioVideo: number; de: number; ate: number; entrada?: "dissolve" | "corte" | "pagina" };
type Apoio = Cena & { rotulo?: [string, string]; saida?: "dissolve" | "corte" | "pagina" };
type Legenda = { de: number; ate: number; texto: string };
export type RoteiroOficina = { fps: number; duracao: number; cenas: Cena[]; apoios: Apoio[]; legendas: Legenda[]; fadeFinal: number;
  // encerramento com a logo a partir de "de": animado (dissolve) ou "cartela" (corte seco para preto + logo parada)
  outro?: { de: number; estilo?: string; dur?: number } };
export const duracaoTotal = (r: { duracao: number; outro?: { de: number; dur?: number } }) =>
  (r.outro ? r.outro.de + (r.outro.dur ?? OUTRO_DUR) : r.duracao);

const FONTE = "Montserrat, sans-serif";
const DISSOLVE = 0.35;
// "pagina": a cena que sai vira como a página de um livro (dobradiça na borda esquerda), centrada no corte
const PAGINA = 0.9;
const viraSuave = Easing.inOut(Easing.sin);
const progressoVirada = (frame: number, inicio: number, fps: number) =>
  interpolate(frame, [Math.round(inicio * fps), Math.round((inicio + PAGINA) * fps)], [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: viraSuave });
const suave = Easing.bezier(0.4, 0, 0.2, 1);
const rampa = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave });

// antes: segundos que a cena começa ANTES de c.de (para já estar por baixo da página que vira)
// virada: 0→1 enquanto ESTA cena vira como página e revela a seguinte
const Video: React.FC<{ c: Cena; ate: number; opacidade: number; fps: number; antes?: number; virada?: number | null }> =
  ({ c, ate, opacidade, fps, antes = 0, virada = null }) => {
    const de = c.de - antes;
    // início e fim arredondados separadamente: cenas vizinhas nunca deixam um quadro vazio (flash branco) entre elas
    const q = (seg: number) => Math.round(seg * fps);
    const pagina: React.CSSProperties = virada === null ? {} : {
      zIndex: 2, transformOrigin: "0% 50%", transform: `rotateY(${-96 * virada}deg)`, backfaceVisibility: "hidden",
      boxShadow: `${40 * virada}px 0 ${90 * virada}px rgba(0,0,0,${0.45 * virada})`,
    };
    return (
      <Sequence from={q(de)} durationInFrames={Math.max(1, q(ate) - q(de))} layout="none">
        <AbsoluteFill style={{ opacity: opacidade, ...pagina }}>
          <OffthreadVideo src={staticFile(c.video)} muted startFrom={Math.max(0, Math.round((c.inicioVideo - antes) * fps))}
            style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          {virada !== null && (   /* o papel escurece do lado da dobra e ganha um brilho na borda que levanta */
            <AbsoluteFill style={{ background: `linear-gradient(to right, rgba(0,0,0,${0.5 * virada}) 0%, rgba(0,0,0,${0.18 * virada}) 55%, rgba(255,255,255,${0.16 * virada}) 100%)` }} />
          )}
        </AbsoluteFill>
      </Sequence>
    );
  };

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
      <AbsoluteFill style={{ isolation: "isolate", perspective: 2600, perspectiveOrigin: "50% 50%" }}>
        {cenas.map((c, i) => {
          const prox = cenas[i + 1];
          const vira = prox?.entrada === "pagina";
          const ate = prox ? prox.de + (prox.entrada === "dissolve" ? DISSOLVE : vira ? PAGINA / 2 : 0) : roteiro.duracao;
          const op = c.entrada === "dissolve" ? rampa(t, c.de, c.de + DISSOLVE) : 1;
          const a = prox ? prox.de - PAGINA / 2 : 0;
          const virada = vira && frame >= Math.round(a * fps) ? progressoVirada(frame, a, fps) : null;
          return (
            <React.Fragment key={i}>
              <Video c={c} ate={ate} opacidade={op} fps={fps} antes={c.entrada === "pagina" ? PAGINA / 2 : 0} virada={virada} />
              {virada !== null && (   /* sombra da página sobre a cena que aparece por baixo */
                <AbsoluteFill style={{ zIndex: 1, opacity: 1 - virada,
                  background: "linear-gradient(to right, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.30) 60%, rgba(0,0,0,0.12) 100%)" }} />
              )}
            </React.Fragment>
          );
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ isolation: "isolate", perspective: 2600, perspectiveOrigin: "50% 50%" }}>
        {roteiro.apoios.map((a, i) => {
          const some = a.saida === "corte" || a.saida === "pagina" ? 1 : 1 - rampa(t, a.ate - 0.28, a.ate);
          const virada = a.saida === "pagina" && frame >= Math.round((a.ate - PAGINA) * fps)
            ? progressoVirada(frame, a.ate - PAGINA, fps) : null;
          return <Video key={`a${i}`} c={a} ate={a.ate} opacidade={rampa(t, a.de, a.de + 0.3) * some} fps={fps} virada={virada} />;
        })}
      </AbsoluteFill>
      {roteiro.apoios.map((a, i) => <Rotulo key={`r${i}`} a={a} t={t} />)}
      {roteiro.legendas.map((l, i) => <LegendaView key={i} l={l} t={t} />)}
      {roteiro.outro?.estilo === "cartela" ? (
        <Sequence from={Math.round(roteiro.outro.de * fps)} layout="none">
          <CartelaLogo />
        </Sequence>
      ) : roteiro.outro ? (
        <Sequence from={Math.round(roteiro.outro.de * fps)} layout="none">
          <AbsoluteFill style={{ opacity: rampa(t, roteiro.outro.de, roteiro.outro.de + 0.6) }}>
            <OutroOficina />
          </AbsoluteFill>
        </Sequence>
      ) : (
        <AbsoluteFill style={{ background: "#fff", opacity: rampa(t, roteiro.duracao - roteiro.fadeFinal, roteiro.duracao) }} />
      )}
      <Audio src={staticFile(audio)} />
    </AbsoluteFill>
  );
};
