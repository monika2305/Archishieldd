import { motion } from "framer-motion";
import { STEPS } from "./data";

export default function HowItWorks() {
  return (
    <section
      id="process"
      className="relative bg-[#0B1220] py-28 sm:py-36"
      data-testid="process-section"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="max-w-2xl">
          <span className="font-mono-tech text-xs uppercase tracking-[0.3em] text-[#14B8A6]">
            / How It Works
          </span>
          <h2 className="font-display mt-5 text-3xl font-bold tracking-tighter text-[#F4F6F9] sm:text-4xl lg:text-5xl">
            From raw IFC to compliant build — in five moves.
          </h2>
        </div>

        <div className="mt-16 border-t border-white/10">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: i * 0.04 }}
              className="group grid grid-cols-1 items-center gap-4 border-b border-white/10 py-8 md:grid-cols-[140px_1fr_1fr] md:gap-10 md:py-10"
              data-testid={`process-step-${s.n}`}
            >
              <span className="font-display text-6xl font-bold leading-none tracking-tighter text-white/[0.08] transition-colors duration-300 group-hover:text-[#14B8A6]/30 md:text-8xl">
                {s.n}
              </span>
              <h3 className="font-display text-2xl font-bold tracking-tight text-[#F4F6F9] md:text-3xl">
                {s.title}
              </h3>
              <p className="max-w-md text-base leading-relaxed text-[#8A94A3]">
                {s.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
