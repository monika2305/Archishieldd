import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { BrokenBuilding, HealedBuilding } from "./Building";
import { DEFECTS, MODULES } from "./data";

gsap.registerPlugin(ScrollTrigger);

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (v, a, b) => {
  const t = clamp((v - a) / (b - a));
  return t * t * (3 - 2 * t);
};

const heroLines = ["Your BIM Model", "Is Hiding", "Costly Errors."];

export default function TransformStage({ onLaunchPlatform }) {
  const sectionRef = useRef(null);
  const pinRef = useRef(null);
  const heroRef = useRef(null);
  const problemRef = useRef(null);
  const diagRef = useRef(null);
  const resultRef = useRef(null);
  const healRef = useRef(null);
  const brokenRef = useRef(null);
  const scanRef = useRef(null);
  const qualityRef = useRef(null);
  const complianceRef = useRef(null);
  const defectRefs = useRef([]);
  const moduleRefs = useRef([]);
  const buildingRef = useRef(null);
  const rotateRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const isMobile = window.matchMedia("(max-width: 767px)").matches;
      const distance = isMobile ? 2600 : 4400;

      const set = (el, props) => el && gsap.set(el, props);

      const st = ScrollTrigger.create({
        trigger: sectionRef.current,
        start: "top top",
        end: `+=${distance}`,
        pin: pinRef.current,
        scrub: 1,
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate: (self) => {
          const p = self.progress;

          // ---- HERO (0 – 0.12) ----
          const heroOut = smooth(p, 0.02, 0.14);
          set(heroRef.current, { autoAlpha: 1 - heroOut, y: -40 * heroOut });

          // ---- PROBLEM (0.14 – 0.42) ----
          const probIn = smooth(p, 0.15, 0.24);
          const probOut = smooth(p, 0.4, 0.46);
          set(problemRef.current, {
            autoAlpha: probIn - probOut,
            y: 30 * (1 - probIn),
          });
          DEFECTS.forEach((_, i) => {
            const s = 0.16 + i * 0.05;
            const a = smooth(p, s, s + 0.05) - probOut;
            set(defectRefs.current[i], { autoAlpha: a, x: 0, scale: 0.9 + 0.1 * clamp(a) });
          });

          // ---- DIAGNOSIS heal (0.44 – 0.86) ----
          const h = smooth(p, 0.44, 0.86);

          // scroll-driven rotation: building slowly turns to face the viewer,
          // completing exactly as the scan begins (p = 0.44), then holds steady.
          const rot = -18 * (1 - smooth(p, 0.06, 0.44));
          set(rotateRef.current, {
            rotationY: rot,
            transformPerspective: 1100,
            transformOrigin: "50% 50%",
          });

          set(healRef.current, {
            clipPath: `inset(0px 0px ${(1 - h) * 100}% 0px)`,
          });
          // broken fades as it heals + result glow
          set(brokenRef.current, { autoAlpha: 1 - smooth(p, 0.5, 0.9) });
          set(buildingRef.current, {
            filter: `drop-shadow(0 0 ${h * 34}px rgba(20,184,166,${0.15 + h * 0.4}))`,
          });

          // scan line visible only mid-heal
          const scanVis = smooth(p, 0.44, 0.5) - smooth(p, 0.82, 0.9);
          set(scanRef.current, {
            autoAlpha: scanVis,
            top: `${clamp(h) * 100}%`,
          });

          // diagnosis panel (scores + modules)
          const diagIn = smooth(p, 0.44, 0.52);
          const diagOut = smooth(p, 0.86, 0.92);
          set(diagRef.current, { autoAlpha: diagIn - diagOut, y: 24 * (1 - diagIn) });

          // counters
          if (qualityRef.current)
            qualityRef.current.textContent = (34 + h * (87.6 - 34)).toFixed(1);
          if (complianceRef.current)
            complianceRef.current.textContent =
              Math.round(41 + h * (96 - 41)) + "%";

          // module chips light up
          const lit = Math.floor(h * MODULES.length + 0.001);
          MODULES.forEach((_, i) => {
            const on = i < lit;
            set(moduleRefs.current[i], {
              borderColor: on ? "rgba(20,184,166,0.6)" : "rgba(255,255,255,0.1)",
              color: on ? "#14B8A6" : "#8A94A3",
              backgroundColor: on ? "rgba(20,184,166,0.08)" : "transparent",
            });
          });

          // ---- RESULT (0.9 – 1) ----
          const resIn = smooth(p, 0.9, 0.98);
          set(resultRef.current, { autoAlpha: resIn, y: 30 * (1 - resIn) });
        },
      });

      // initial states
      set(problemRef.current, { autoAlpha: 0 });
      set(diagRef.current, { autoAlpha: 0 });
      set(resultRef.current, { autoAlpha: 0 });
      set(scanRef.current, { autoAlpha: 0 });
      set(healRef.current, { clipPath: "inset(0px 0px 100% 0px)" });
      set(rotateRef.current, {
        rotationY: -18,
        transformPerspective: 1100,
        transformOrigin: "50% 50%",
      });
      defectRefs.current.forEach((el) => set(el, { autoAlpha: 0 }));

      const refresh = () => ScrollTrigger.refresh();
      const t = setTimeout(refresh, 400);
      window.addEventListener("load", refresh);
      return () => {
        clearTimeout(t);
        window.removeEventListener("load", refresh);
        st.kill();
      };
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative" data-testid="transform-stage">
      <div
        ref={pinRef}
        className="relative flex h-screen w-full items-center justify-center overflow-hidden"
      >
        <div className="absolute inset-0 bp-grid" />
        <div className="absolute inset-0 bp-dots opacity-40" />
        <div className="pointer-events-none absolute inset-0 vignette" />

        {/* ---------------- CENTER BUILDING ---------------- */}
        <div
          ref={buildingRef}
          className="relative z-10 h-[46vh] max-h-[560px] w-[240px] translate-y-[22%] px-2 sm:h-[62vh] sm:w-[400px] sm:translate-y-0"
          style={{ perspective: "1100px" }}
        >
          <div ref={rotateRef} className="absolute inset-0 [transform-style:preserve-3d]">
            <div ref={brokenRef} className="absolute inset-0">
              <BrokenBuilding className="h-full w-full" />
            </div>
            <div ref={healRef} className="absolute inset-0">
              <HealedBuilding className="h-full w-full" />
            </div>
          </div>
          {/* radar scan line */}
          <div
            ref={scanRef}
            className="pointer-events-none absolute left-[-8%] right-[-8%] z-20"
            style={{ top: "0%" }}
          >
            <div className="h-[2px] w-full bg-[#14B8A6] shadow-[0_0_22px_4px_rgba(20,184,166,0.8)]" />
            <div className="h-10 w-full bg-gradient-to-b from-[#14B8A6]/25 to-transparent" />
          </div>
        </div>

        {/* ---------------- HERO overlay ---------------- */}
        <div
          ref={heroRef}
          className="absolute inset-0 z-30 mx-auto flex max-w-7xl flex-col justify-start px-5 pt-24 sm:justify-center sm:px-8 sm:pt-0"
        >
          <div className="max-w-xl">
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="font-mono-tech inline-flex items-center gap-2 rounded-full border border-[#E8743B]/40 bg-[#E8743B]/10 px-4 py-1.5 text-[11px] uppercase tracking-[0.2em] text-[#E8743B]"
            >
              <span className="crack-pulse h-1.5 w-1.5 rounded-full bg-[#E24C3F]" />
              4 critical defects detected
            </motion.span>

            <h1 className="font-display mt-6 text-4xl font-bold leading-[1.02] tracking-tighter text-[#F4F6F9] sm:text-6xl">
              {heroLines.map((line, i) => (
                <span key={i} className="reveal-mask">
                  <motion.span
                    className="block"
                    initial={{ y: "110%" }}
                    animate={{ y: "0%" }}
                    transition={{
                      delay: 0.35 + i * 0.12,
                      duration: 0.85,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  >
                    {i === 2 ? (
                      <span className="text-[#E8743B] text-glow-error">{line}</span>
                    ) : (
                      line
                    )}
                  </motion.span>
                </span>
              ))}
            </h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8, duration: 0.7 }}
              className="mt-6 max-w-md text-lg leading-relaxed text-[#8A94A3]"
            >
              ArchiShield — AI-powered BIM quality &amp; compliance intelligence.{" "}
              <span className="text-[#F4F6F9]/90">
                Engineering the Future of Intelligent Construction.
              </span>
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.95, duration: 0.7 }}
              className="mt-8 flex items-center gap-4"
            >
              <button
                onClick={onLaunchPlatform}
                data-testid="hero-get-started"
                className="group inline-flex items-center gap-2 rounded-full bg-[#0F9B8E] px-7 py-3.5 text-base font-semibold text-white transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:bg-[#14B8A6] hover:shadow-[0_0_36px_-4px_rgba(20,184,166,0.75)] cursor-pointer border-0"
              >
                Get Started
                <span className="transition-transform duration-300 group-hover:translate-x-0.5">
                  →
                </span>
              </button>
              <span className="font-mono-tech text-xs uppercase tracking-[0.15em] text-[#8A94A3]">
                Scroll to diagnose ↓
              </span>
            </motion.div>
          </div>
        </div>

        {/* ---------------- PROBLEM overlay ---------------- */}
        <div ref={problemRef} className="absolute inset-0 z-30">
          <div className="mx-auto flex h-full max-w-7xl items-start px-5 pt-24 sm:items-center sm:px-8 sm:pt-0">
            <div className="max-w-sm">
              <span id="problem" className="font-mono-tech text-xs uppercase tracking-[0.3em] text-[#E8743B]">
                / The Problem
              </span>
              <h2 className="font-display mt-4 text-3xl font-bold tracking-tighter text-[#F4F6F9] sm:text-4xl">
                Undetected until it&apos;s expensive.
              </h2>
              <p className="mt-4 text-base leading-relaxed text-[#8A94A3]">
                Invalid proxy elements, missing property sets and geometry errors
                slip past manual review — and non-compliance with India&apos;s
                <span className="text-[#F4F6F9]/90"> NBC 2016</span> surfaces only
                on site, as costly rework.
              </p>
            </div>
          </div>
          {/* defect labels tagging the building */}
          {DEFECTS.map((d, i) => (
            <div
              key={d.id}
              ref={(el) => (defectRefs.current[i] = el)}
              className={`absolute z-40 ${
                d.side === "left"
                  ? "left-[8%] sm:left-[24%]"
                  : "right-[8%] sm:right-[24%]"
              }`}
              style={{ top: d.top }}
              data-testid={`defect-label-${d.id}`}
            >
              <span className="font-mono-tech flex items-center gap-2 rounded-md border border-[#E8743B]/50 bg-[#0B1220]/90 px-3 py-2 text-[11px] uppercase tracking-[0.15em] text-[#E8743B] backdrop-blur">
                <span className="crack-pulse h-1.5 w-1.5 rounded-full bg-[#E24C3F]" />
                {d.label}
              </span>
            </div>
          ))}
        </div>

        {/* ---------------- DIAGNOSIS overlay ---------------- */}
        <div ref={diagRef} className="absolute inset-0 z-30">
          <div className="mx-auto flex h-full max-w-7xl items-start justify-center px-5 pt-24 sm:items-center sm:justify-end sm:px-8 sm:pt-0">
            <div className="w-full max-w-xs">
              <span id="diagnosis" className="font-mono-tech text-xs uppercase tracking-[0.3em] text-[#14B8A6]">
                / Diagnosing
              </span>
              <div className="mt-5 space-y-4">
                <div className="rounded-lg border border-white/10 bg-[#111A2C]/80 p-5 backdrop-blur">
                  <div className="font-mono-tech text-[11px] uppercase tracking-[0.15em] text-[#8A94A3]">
                    Model Quality Score
                  </div>
                  <div className="font-mono-tech mt-1 text-4xl font-bold text-[#14B8A6] text-glow-teal">
                    <span ref={qualityRef}>34.0</span>
                    <span className="text-lg text-[#8A94A3]"> / 100</span>
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-[#111A2C]/80 p-5 backdrop-blur">
                  <div className="font-mono-tech text-[11px] uppercase tracking-[0.15em] text-[#8A94A3]">
                    NBC 2016 Compliance
                  </div>
                  <div className="font-mono-tech mt-1 text-4xl font-bold text-[#14B8A6] text-glow-teal">
                    <span ref={complianceRef}>41%</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-1.5">
                {MODULES.map((m, i) => (
                  <span
                    key={m.id}
                    ref={(el) => (moduleRefs.current[i] = el)}
                    className="font-mono-tech rounded border border-white/10 px-2 py-1.5 text-[9px] uppercase tracking-[0.1em] text-[#8A94A3]"
                    style={{ transition: "none" }}
                  >
                    {m.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ---------------- RESULT overlay ---------------- */}
        <div
          ref={resultRef}
          className="absolute inset-0 z-30 mx-auto flex max-w-7xl flex-col justify-start px-5 pt-24 sm:justify-center sm:px-8 sm:pt-0"
        >
          <div className="max-w-xl">
            <span className="font-mono-tech inline-flex items-center gap-2 rounded-full border border-[#14B8A6]/40 bg-[#14B8A6]/10 px-4 py-1.5 text-[11px] uppercase tracking-[0.2em] text-[#14B8A6]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#14B8A6]" />
              Model restored — 0 critical defects
            </span>
            <h2 className="font-display mt-6 text-4xl font-bold leading-[1.04] tracking-tighter text-[#F4F6F9] sm:text-6xl">
              Flawless Models.
              <br />
              Compliant Builds.
              <br />
              <span className="text-[#14B8A6] text-glow-teal">Zero Surprises.</span>
            </h2>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-[#8A94A3]">
              Faster approvals, no on-site rework, and NBC-compliant deliverables
              from day one — every element validated at the source.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
