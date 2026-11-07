import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const Main: React.FC<{ titulo: string }> = ({ titulo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#1d1b2f",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ fontSize: 220, transform: `scale(${scale})` }}>🐶</div>
      <h1 style={{ color: "white", fontSize: 110, opacity }}>{titulo}</h1>
    </AbsoluteFill>
  );
};
