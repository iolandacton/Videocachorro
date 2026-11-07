import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate,
  staticFile, useCurrentFrame,
} from "remotion";

// Prévia de 5 s montada SÓ com os arquivos originais (sem IA generativa).
// Áudio: som real gravado pela Insta360, alinhado ao trecho de vídeo usado.
const FPS = 30;
const SRC_OFFSET = Math.round(0.4 * FPS); // composição f ↔ fonte 0.4s + f
const CUT = 33; // início da transição foto → praia (1.1 s)
const FADE = 15;

export const Cena01Preview: React.FC = () => {
  const f = useCurrentFrame();
  const fotoZoom = interpolate(f, [0, CUT + FADE], [1.0, 1.1]);
  const bob = Math.sin(f / 3.2) * 6; // leve balanço do trote
  const praiaOpacity = interpolate(f, [CUT, CUT + FADE], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={{ transform: `scale(${fotoZoom}) translateY(${bob}px)` }}>
        <Img src={staticFile("originais/yorkshire_costas.jpg")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>

      <Sequence from={CUT}>
        <AbsoluteFill style={{ opacity: praiaOpacity }}>
          {/* zoom ancorado no topo: corta a marca d'água Insta360 do rodapé */}
          <AbsoluteFill style={{ transform: "scale(1.12)", transformOrigin: "50% 0%" }}>
            <OffthreadVideo muted src={staticFile("originais/praia_insta360.mov")}
              startFrom={SRC_OFFSET + CUT}
              style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </AbsoluteFill>
        </AbsoluteFill>
      </Sequence>

      <Audio src={staticFile("originais/praia_insta360.mov")} startFrom={SRC_OFFSET}
        volume={(fr) => interpolate(fr, [0, 10, 135, 150], [0, 1, 1, 0], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
    </AbsoluteFill>
  );
};
