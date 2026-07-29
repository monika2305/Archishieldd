import { motion } from "framer-motion";
import { HealedBuilding } from "./Building";

export default function FinalCTA({ onLaunchPlatform }) {
  return (
    <section
      id="cta"
      className="relative overflow-hidden border-t border-white/10 bg-[#0B1220]"
      data-testid="cta-section"
    >
      <div className="absolute inset-0 bp-grid opacity-50" />
      <div className="pointer-events-none absolute inset-0 vignette" />

      <div className="relative mx-auto max-w-5xl px-5 py-32 text-center sm:px-8 sm:py-44">
        <motion.span
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="font-mono-tech text-xs uppercase tracking-[0.35em] text-[#14B8A6]"
        >
          Engineering the Future of Intelligent Construction
        </motion.span>

        <motion.h2
          initial={{ opacity: 0, y: 34 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="font-display mx-auto mt-6 max-w-3xl text-4xl font-bold leading-[1.05] tracking-tighter text-[#F4F6F9] sm:text-6xl"
        >
          Ship models the code can{" "}
          <span className="text-[#14B8A6] text-glow-teal">approve on sight.</span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-[#8A94A3]"
        >
          Bring ArchiShield into your BIM workflow and turn every submission into
          a compliant, defect-free deliverable — from day one.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-11"
        >
          <button
            onClick={onLaunchPlatform}
            data-testid="cta-get-started"
            className="group inline-flex items-center gap-3 rounded-full bg-[#0F9B8E] px-10 py-5 text-lg font-semibold text-white transition-[transform,box-shadow] duration-300 glow-teal-soft hover:-translate-y-1 hover:bg-[#14B8A6] hover:shadow-[0_0_50px_-4px_rgba(20,184,166,0.85)] cursor-pointer border-0"
          >
            Get Started
            <span className="transition-transform duration-300 group-hover:translate-x-1">
              →
            </span>
          </button>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="relative border-t border-white/10">
        <div className="pointer-events-none absolute inset-0 flex items-end justify-center overflow-hidden">
          <span className="font-display translate-y-1/4 select-none text-[24vw] font-bold leading-none tracking-tighter text-white/[0.02]">
            ArchiShield
          </span>
        </div>
        <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-10 px-5 py-20 sm:px-8 md:grid-cols-[1.2fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-md border border-[#14B8A6]/50 bg-[#0F9B8E]/10">
                <span className="font-display text-sm font-bold tracking-tight text-[#14B8A6]">
                  AT
                </span>
              </span>
              <span className="font-display text-[15px] font-bold tracking-tight text-[#F4F6F9]">
                ArchiTechs
              </span>
            </div>
            <p className="mt-5 max-w-xs text-sm leading-relaxed text-[#8A94A3]">
              AI-powered BIM quality &amp; compliance intelligence for the Indian
              construction industry.
            </p>
          </div>
          <div>
            <span className="font-mono-tech text-[11px] uppercase tracking-[0.2em] text-[#8A94A3]">
              Product
            </span>
            <ul className="mt-4 space-y-3 text-sm text-[#F4F6F9]/80" style={{ listStyle: 'none', padding: 0 }}>
              <li><a href="#modules" className="hover:text-[#14B8A6]" style={{ textDecoration: 'none', color: 'inherit' }}>Modules</a></li>
              <li><a href="#diagnosis" className="hover:text-[#14B8A6]" style={{ textDecoration: 'none', color: 'inherit' }}>Diagnosis Engine</a></li>
              <li><a href="#process" className="hover:text-[#14B8A6]" style={{ textDecoration: 'none', color: 'inherit' }}>How It Works</a></li>
            </ul>
          </div>
          <div>
            <span className="font-mono-tech text-[11px] uppercase tracking-[0.2em] text-[#8A94A3]">
              Standards
            </span>
            <ul className="mt-4 space-y-3 text-sm text-[#F4F6F9]/80" style={{ listStyle: 'none', padding: 0 }}>
              <li>NBC 2016 Compliance</li>
              <li>IFC2x3 / IFC4</li>
              <li>BuildingSMART BCF</li>
            </ul>
          </div>
        </div>
        <div className="relative border-t border-white/10 py-6">
          <p className="mx-auto max-w-7xl px-5 font-mono-tech text-[11px] uppercase tracking-[0.2em] text-[#8A94A3] sm:px-8">
            © {new Date().getFullYear()} ArchiTechs — Engineering the Future of Intelligent Construction
          </p>
        </div>
        <div className="pointer-events-none absolute right-8 top-8 hidden h-24 w-24 opacity-40 md:block">
          <HealedBuilding className="h-full w-full" />
        </div>
      </footer>
    </section>
  );
}
