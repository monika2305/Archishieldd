/*
 * Custom isometric building illustration.
 * Two matched layers share identical geometry so the "healed" layer can be
 * revealed on top of the "broken" layer via a clip-path scan reveal.
 */

const CX = 200;
const BASE_Y = 452;
const HALF_W = 92; // horizontal half-width of iso footprint
const DEPTH = 46; // iso vertical offset
const FH = 40; // floor height
const FLOORS = 8;

function floor(i, dx = 0) {
  const cy = BASE_Y - i * FH;
  const cxi = CX + dx;
  const top = { x: cxi, y: cy - DEPTH };
  const right = { x: cxi + HALF_W, y: cy };
  const bottom = { x: cxi, y: cy + DEPTH };
  const left = { x: cxi - HALF_W, y: cy };
  return { cy, top, right, bottom, left, cxi };
}

const poly = (pts) => pts.map((p) => `${p.x},${p.y}`).join(" ");

// Roof rhombus (top face)
function roofPts(f) {
  return [f.top, f.right, f.bottom, f.left];
}
// Left wall of a floor (extends down by FH)
function leftWall(f) {
  return [
    f.left,
    f.bottom,
    { x: f.bottom.x, y: f.bottom.y + FH },
    { x: f.left.x, y: f.left.y + FH },
  ];
}
// Right wall of a floor
function rightWall(f) {
  return [
    f.bottom,
    f.right,
    { x: f.right.x, y: f.right.y + FH },
    { x: f.bottom.x, y: f.bottom.y + FH },
  ];
}
// Window mullion lines on a wall face (a few horizontal/vertical strokes)
function faceLines(a, b, count) {
  const lines = [];
  for (let k = 1; k < count; k++) {
    const t = k / count;
    lines.push({
      x1: a.x + (b.x - a.x) * t,
      y1: a.y + (b.y - a.y) * t,
      x2: a.x + (b.x - a.x) * t,
      y2: a.y + (b.y - a.y) * t + FH,
    });
  }
  return lines;
}

const floorsData = Array.from({ length: FLOORS }, (_, i) =>
  floor(i, i === FLOORS - 1 ? 14 : 0),
);

/* ---------------- HEALED (clean teal) ---------------- */
export function HealedBuilding({ className = "", style }) {
  const teal = "#14B8A6";
  const tealDim = "rgba(20,184,166,0.85)";
  return (
    <svg
      viewBox="-20 -12 440 584"
      className={className}
      style={style}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="tealFace" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(20,184,166,0.16)" />
          <stop offset="100%" stopColor="rgba(15,155,142,0.05)" />
        </linearGradient>
        <filter id="tealGlow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="3.2" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* base pad */}
      <polygon
        points={poly([
          { x: CX, y: BASE_Y + DEPTH + 18 },
          { x: CX + HALF_W + 26, y: BASE_Y + 4 },
          { x: CX, y: BASE_Y - DEPTH - 14 },
          { x: CX - HALF_W - 26, y: BASE_Y + 4 },
        ])}
        fill="rgba(20,184,166,0.05)"
        stroke="rgba(20,184,166,0.35)"
        strokeWidth="1"
      />

      <g filter="url(#tealGlow)">
        {floorsData.map((f, i) => (
          <g key={i}>
            <polygon points={poly(leftWall(f))} fill="url(#tealFace)" stroke={teal} strokeWidth="1.5" strokeLinejoin="round" />
            <polygon points={poly(rightWall(f))} fill="rgba(15,155,142,0.10)" stroke={teal} strokeWidth="1.5" strokeLinejoin="round" />
            {faceLines(f.left, f.bottom, 3).map((l, k) => (
              <line key={"l" + k} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} stroke={tealDim} strokeWidth="0.75" />
            ))}
            {faceLines(f.bottom, f.right, 3).map((l, k) => (
              <line key={"r" + k} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} stroke={tealDim} strokeWidth="0.75" />
            ))}
            <polygon points={poly(roofPts(f))} fill="rgba(20,184,166,0.12)" stroke={teal} strokeWidth="1.5" strokeLinejoin="round" />
          </g>
        ))}
      </g>
    </svg>
  );
}

/* ---------------- BROKEN (error orange-red) ---------------- */
export function BrokenBuilding({ className = "", style }) {
  const err = "#E8743B";
  const errBright = "#E24C3F";
  const missing = new Set([3, 6]); // floors with a missing wall
  return (
    <svg
      viewBox="-20 -12 440 584"
      className={className}
      style={style}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="errFace" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(232,116,59,0.14)" />
          <stop offset="100%" stopColor="rgba(226,76,63,0.04)" />
        </linearGradient>
      </defs>

      {/* fractured base pad */}
      <polygon
        points={poly([
          { x: CX, y: BASE_Y + DEPTH + 18 },
          { x: CX + HALF_W + 26, y: BASE_Y + 4 },
          { x: CX + 8, y: BASE_Y - DEPTH - 12 },
          { x: CX - HALF_W - 20, y: BASE_Y + 10 },
        ])}
        fill="rgba(232,116,59,0.05)"
        stroke="rgba(232,116,59,0.4)"
        strokeWidth="1"
        strokeDasharray="6 5"
      />

      {floorsData.map((f, i) => {
        const showLeft = !(missing.has(i));
        const showRight = !(i === 6);
        const jitter = i >= 5 ? (i - 4) * 2 : 0;
        return (
          <g key={i} transform={`translate(${jitter}, 0)`}>
            {showLeft && (
              <polygon points={poly(leftWall(f))} fill="url(#errFace)" stroke={err} strokeWidth="1.5" strokeLinejoin="round" />
            )}
            {showRight && (
              <polygon points={poly(rightWall(f))} fill="rgba(226,76,63,0.06)" stroke={err} strokeWidth="1.5" strokeLinejoin="round" />
            )}
            {/* roof — top floor tilted / detached */}
            <polygon
              points={poly(roofPts(f))}
              fill="rgba(232,116,59,0.08)"
              stroke={err}
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeDasharray={missing.has(i) ? "5 4" : "0"}
            />
          </g>
        );
      })}

      {/* jagged crack running down the facade */}
      <polyline
        className="crack-pulse"
        points="176,150 190,196 168,232 196,286 172,330 198,388"
        fill="none"
        stroke={errBright}
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        className="crack-pulse"
        style={{ animationDelay: "0.8s" }}
        points="236,232 250,266 232,300 256,344"
        fill="none"
        stroke={errBright}
        strokeWidth="1.8"
        strokeLinecap="round"
      />

      {/* error nodes pulsing */}
      {[
        { x: 176, y: 150 },
        { x: 262, y: 214 },
        { x: 150, y: 300 },
        { x: 268, y: 350 },
        { x: 200, y: 118 },
      ].map((n, i) => (
        <g key={i} className="crack-pulse" style={{ animationDelay: `${i * 0.4}s` }}>
          <circle cx={n.x} cy={n.y} r="6" fill="none" stroke={errBright} strokeWidth="1.6" />
          <circle cx={n.x} cy={n.y} r="2" fill={errBright} />
        </g>
      ))}
    </svg>
  );
}
