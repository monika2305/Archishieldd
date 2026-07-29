import { useEffect, useRef, useState } from "react";
import { motion, useInView, animate } from "framer-motion";
import {
  Tag,
  ClipboardList,
  Layers,
  ShieldCheck,
  Gauge,
  Scale,
  Grid3x3,
  Boxes,
  GitCompare,
  Wrench,
  Upload,
  MessageSquare,
} from "lucide-react";
import { MODULES } from "./data";
import { HealedBuilding } from "./Building";

const ICONS = {
  proxy: Tag,
  pset: ClipboardList,
  storey: Layers,
  nbc: ShieldCheck,
  score: Gauge,
  rule: Scale,
  heatmap: Grid3x3,
  geometry: Boxes,
  version: GitCompare,
  correction: Wrench,
  bcf: Upload,
  nlq: MessageSquare,
};

const row = {
  hidden: { clipPath: "inset(0 100% 0 0)", opacity: 0.35 },
  show: {
    clipPath: "inset(0 0% 0 0)",
    opacity: 1,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  },
};

function ScoreCounter({ to = 87.6 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, to, {
      duration: 1.6,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setVal(v),
    });
    return () => controls.stop();
  }, [inView, to]);
  return (
    <span ref={ref} className="font-mono-tech tabular-nums">
      {val.toFixed(1)}
    </span>
  );
}

function ModuleRow({ m, i }) {
  const Icon = ICONS[m.id];
  return (
    <motion.div
      variants={row}
      className="group relative border-b border-white/10"
      data-testid={`module-card-${m.id}`}
    >
      {/* teal left border on hover */}
      <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] origin-top scale-y-0 bg-[#14B8A6] shadow-[0_0_12px_rgba(20,184,166,0.7)] transition-transform duration-300 ease-out group-hover:scale-y-100" />
      {/* dotted connector aiming toward the building silhouette on the left */}
      <span className="pointer-events-none absolute left-0 top-1/2 hidden h-px w-14 origin-right -translate-x-full scale-x-0 border-t border-dashed border-[#14B8A6]/70 opacity-0 transition-[transform,opacity] duration-300 ease-out group-hover:scale-x-100 group-hover:opacity-100 lg:block" />

      <div className="flex items-start gap-4 py-5 pl-4 pr-2 transition-colors duration-300 group-hover:bg-white/[0.015] sm:gap-5 sm:pl-6">
        <span className="font-mono-tech mt-0.5 shrink-0 text-sm tracking-[0.15em] text-[#8A94A3] transition-[color,text-shadow] duration-300 group-hover:text-[#14B8A6] group-hover:[text-shadow:0_0_14px_rgba(20,184,166,0.85)]">
          {String(i + 1).padStart(2, "0")}
        </span>

        {/* tick / oscilloscope mark */}
        <span className="mt-2 hidden h-px w-6 shrink-0 bg-[#8A94A3]/30 transition-colors duration-300 group-hover:bg-[#14B8A6]/60 sm:block" />

        {Icon && (
          <Icon
            className="mt-0.5 h-5 w-5 shrink-0 text-[#14B8A6]"
            strokeWidth={1.5}
            aria-hidden="true"
          />
        )}

        <div className="min-w-0">
          <h3 className="font-display text-lg font-bold leading-tight tracking-tight text-[#F4F6F9]">
            {m.name}
          </h3>
          <p className="mt-1.5 text-sm leading-relaxed text-[#8A94A3]">
            {m.desc}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export default function Modules() {
  return (
    <section
      id="modules"
      className="relative overflow-x-clip bg-[#0B1220] py-28 sm:py-36"
      data-testid="modules-section"
    >
      <div className="absolute inset-0 bp-grid opacity-50" />

      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        {/* headline */}
        <div className="max-w-2xl">
          <span className="font-mono-tech text-xs uppercase tracking-[0.3em] text-[#14B8A6]">
            / The Diagnostic Engine
          </span>
          <h2 className="font-display mt-5 text-3xl font-bold tracking-tighter text-[#F4F6F9] sm:text-4xl lg:text-5xl">
            Twelve modules.{" "}
            <span className="relative inline-block whitespace-nowrap">
              One verdict
              <motion.span
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
                className="absolute -bottom-1 left-0 h-[3px] w-full origin-left rounded-full bg-[#14B8A6] shadow-[0_0_16px_rgba(20,184,166,0.8)]"
              />
            </span>{" "}
            on your model.
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-[#8A94A3]">
            Every ArchiShield analysis runs the full intelligence stack against
            your IFC — a live inspection of your model, module by module.
          </p>
        </div>

        {/* scan layout */}
        <div className="mt-16 grid grid-cols-1 gap-12 lg:grid-cols-[30%_1fr] lg:gap-14">
          {/* LEFT — persistent building silhouette with scan line */}
          <div className="lg:sticky lg:top-28 lg:self-start" data-testid="scan-building">
            <div className="relative mx-auto w-full max-w-[240px] rounded-lg border border-white/10 bg-[#111A2C]/60 p-6 lg:mx-0">
              <div className="font-mono-tech flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-[#8A94A3]">
                <span className="flex items-center gap-2">
                  <span className="crack-pulse h-1.5 w-1.5 rounded-full bg-[#14B8A6]" />
                  Analyzing
                </span>
                <span>IFC · LIVE</span>
              </div>
              <div className="relative mt-4 h-[260px] overflow-hidden">
                <HealedBuilding className="breathe h-full w-full" />
                {/* looping scan line */}
                <div
                  className="scan-vert pointer-events-none absolute left-[-6%] right-[-6%]"
                  style={{ top: "4%" }}
                >
                  <div className="h-[2px] w-full bg-[#14B8A6] shadow-[0_0_18px_3px_rgba(20,184,166,0.75)]" />
                  <div className="h-8 w-full bg-gradient-to-b from-[#14B8A6]/25 to-transparent" />
                </div>
              </div>
              <div className="font-mono-tech mt-4 flex items-center justify-between border-t border-white/10 pt-3 text-[10px] uppercase tracking-[0.16em] text-[#8A94A3]">
                <span>12 modules</span>
                <span className="text-[#14B8A6]">active</span>
              </div>
            </div>
          </div>

          {/* RIGHT — terminal-style module readout */}
          <div>
            <motion.div
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-60px" }}
              transition={{ staggerChildren: 0.09 }}
              className="border-t border-white/10"
            >
              {MODULES.map((m, i) => (
                <ModuleRow key={m.id} m={m} i={i} />
              ))}
            </motion.div>

            {/* final summary payoff */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="mt-8 flex flex-col gap-4 rounded-lg border border-[#14B8A6]/30 bg-[#14B8A6]/[0.06] p-6 sm:flex-row sm:items-center sm:justify-between"
              data-testid="modules-summary"
            >
              <div className="font-display text-2xl font-bold tracking-tight text-[#F4F6F9] sm:text-3xl">
                12 checks. <span className="text-[#14B8A6]">1 score.</span>
              </div>
              <div className="flex items-baseline gap-3">
                <span className="font-mono-tech text-[10px] uppercase tracking-[0.2em] text-[#8A94A3]">
                  Model Quality Score
                </span>
                <span className="font-mono-tech text-4xl font-bold text-[#14B8A6] text-glow-teal sm:text-5xl">
                  <ScoreCounter to={87.6} />
                </span>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
