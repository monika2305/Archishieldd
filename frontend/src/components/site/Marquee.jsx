import { MARQUEE } from "./data";

export default function Marquee() {
  const items = [...MARQUEE, ...MARQUEE];
  return (
    <section
      className="relative overflow-hidden border-y border-white/10 bg-[#0B1220] py-6"
      data-testid="marquee"
      aria-hidden="true"
    >
      <div className="marquee-track">
        {items.map((t, i) => (
          <span key={i} className="flex items-center">
            <span className="font-display px-8 text-2xl font-medium tracking-tight text-[#F4F6F9]/70 sm:text-3xl">
              {t}
            </span>
            <span className="text-[#14B8A6]">◆</span>
          </span>
        ))}
      </div>
    </section>
  );
}
