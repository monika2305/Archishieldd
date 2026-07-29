import { motion } from "framer-motion";

export default function Nav({ onLaunchPlatform }) {
  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
      className="fixed top-0 left-0 z-50 w-full border-b border-white/10 backdrop-blur-xl"
      style={{ backgroundColor: "rgba(11,18,32,0.8)" }}
      data-testid="site-nav"
    >
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3.5 sm:px-8">
        <a href="#" className="flex items-center gap-3" data-testid="nav-logo" onClick={(e) => e.preventDefault()}>
          <span className="relative flex h-9 w-9 items-center justify-center rounded-md border border-[#14B8A6]/50 bg-[#0F9B8E]/10">
            <span className="font-display text-sm font-bold tracking-tight text-[#14B8A6]">
              AT
            </span>
            <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-[#14B8A6]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-[15px] font-bold tracking-tight text-[#F4F6F9]">
              ArchiShield
            </span>
            <span className="font-mono-tech text-[9px] uppercase tracking-[0.28em] text-[#8A94A3]">
              by ArchiTechs
            </span>
          </span>
        </a>

        <div className="hidden items-center gap-8 md:flex">
          {[
            ["Problem", "#problem"],
            ["Diagnosis", "#diagnosis"],
            ["Modules", "#modules"],
            ["Process", "#process"],
          ].map(([label, href]) => (
            <a
              key={label}
              href={href}
              className="font-mono-tech text-xs uppercase tracking-[0.15em] text-[#8A94A3] transition-colors hover:text-[#F4F6F9]"
              data-testid={`nav-link-${label.toLowerCase()}`}
            >
              {label}
            </a>
          ))}
        </div>

        <button
          onClick={onLaunchPlatform}
          data-testid="nav-get-started"
          className="group inline-flex items-center gap-2 rounded-full bg-[#0F9B8E] px-5 py-2.5 text-sm font-semibold text-white transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:bg-[#14B8A6] hover:shadow-[0_0_28px_-4px_rgba(20,184,166,0.7)] cursor-pointer border-0"
        >
          Get Started
          <span className="transition-transform duration-300 group-hover:translate-x-0.5">
            →
          </span>
        </button>
      </nav>
    </motion.header>
  );
}
