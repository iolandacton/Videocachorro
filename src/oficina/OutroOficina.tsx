import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Encerramento OFICINA 7 (6 s, 9:16) — marcenaria de alto padrão.
// Fundo: dolly-in gerado no Veo 3.1 Fast (Runway) a partir do quadro do painel ripado de carvalho, INVERTIDO
// (frames r_0000…r_0191, 24 fps): começa no macro do veio da madeira e recua até o painel inteiro.
// A logo é o arquivo REAL da marca (PNG branco com transparência), aplicada aqui — nunca gerada por IA:
// a luz do ambiente baixa, o nome se revela da esquerda para a direita, um brilho percorre as letras e a
// linha "MÓVEIS PLANEJADOS" sobe em seguida.

export const OUTRO_DUR = 6;
const N_FRAMES = 192, SRC_FPS = 24;
const S0 = 3.2, V = 29.97 / 24, T_EASE = 2.69, DUR = 5;   // 1 quadro da fonte por quadro do vídeo; para em t=5 s
const fonte = (t: number) => {
  if (t <= T_EASE) return S0 + V * t;
  const u = Math.min((t - T_EASE) / (DUR - T_EASE), 1);
  return S0 + V * T_EASE + V * (DUR - T_EASE) * (u - u * u / 2);
};
const quadro = (i: number) =>
  staticFile(`oficina/outro/frames/r_${String(Math.max(0, Math.min(N_FRAMES - 1, i))).padStart(4, "0")}.jpg`);
const ease = Easing.bezier(0.45, 0, 0.2, 1);
const r = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

const LOGO = "oficina/logo/oficina7_branco.png";   // 1728x452: nome em cima (até ~66% da altura), assinatura embaixo
const LARG = 780, ALT = LARG * 452 / 1728, CORTE = 70;   // % da altura onde termina o nome

export const OutroOficina: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = Math.min(fonte(t) * SRC_FPS, N_FRAMES - 1);
  const i0 = Math.floor(s), frac = s - i0;
  const img = { width: "100%", height: "100%", objectFit: "cover" as const, position: "absolute" as const };

  const escurece = r(t, 2.5, 3.9);           // a luz do ambiente baixa para a logo
  const nome = r(t, 3.0, 4.15);              // revelação do nome (esquerda → direita)
  const brilho = r(t, 3.9, 5.1);             // brilho percorrendo as letras
  const linha = r(t, 3.75, 4.6);             // "MÓVEIS PLANEJADOS"
  const logo = `url(${staticFile(LOGO)})`;
  const camada: React.CSSProperties = { position: "absolute", left: 0, top: 0, width: LARG, height: ALT,
    backgroundImage: logo, backgroundSize: "100% 100%" };
  const borda = -12 + 124 * nome;            // posição (em %) da frente da revelação, com borda suave
  const mascara = `linear-gradient(to right, #000 ${borda - 12}%, transparent ${borda}%)`;
  return (
    <AbsoluteFill style={{ background: "#15110d" }}>
      <AbsoluteFill style={{ transform: "scale(1.04)" }}>
        <Img src={quadro(i0)} style={img} />
        <Img src={quadro(i0 + 1)} style={{ ...img, opacity: frac }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `rgba(12,9,6,${0.50 * escurece})` }} />
      <AbsoluteFill style={{ opacity: escurece,
        background: "radial-gradient(ellipse 75% 34% at 50% 47%, rgba(8,6,4,0.55) 0%, rgba(8,6,4,0.30) 55%, rgba(8,6,4,0) 100%)" }} />
      <AbsoluteFill style={{ alignItems: "center" }}>
        <div style={{ position: "absolute", top: 902 - ALT / 2, width: LARG, height: ALT,
          filter: "drop-shadow(0 2px 14px rgba(0,0,0,0.45))" }}>
          <div style={{ ...camada, clipPath: `inset(0 0 ${100 - CORTE}% 0)`, WebkitMaskImage: mascara, maskImage: mascara,
            transform: `scale(${1.035 - 0.035 * nome})`, opacity: Math.min(1, nome * 3) }} />
          {/* brilho: faixa de luz inclinada que percorre o nome, recortada pelo próprio desenho da logo */}
          <div style={{ position: "absolute", left: 0, top: 0, width: LARG, height: ALT, clipPath: `inset(0 0 ${100 - CORTE}% 0)`,
            WebkitMaskImage: logo, maskImage: logo, WebkitMaskSize: "100% 100%", maskSize: "100% 100%",
            opacity: Math.sin(Math.PI * brilho) * 0.9,
            background: `linear-gradient(105deg, rgba(255,236,200,0) ${-30 + 150 * brilho}%, rgba(255,236,200,1) ${-18 + 150 * brilho}%, rgba(255,236,200,0) ${-6 + 150 * brilho}%)` }} />
          <div style={{ ...camada, clipPath: `inset(${CORTE}% 0 0 0)`, opacity: linha, transform: `translateY(${10 * (1 - linha)}px)` }} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "#000", opacity: r(t, OUTRO_DUR - 0.35, OUTRO_DUR) * 0.0 }} />
    </AbsoluteFill>
  );
};
