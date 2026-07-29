import { useEffect } from "react";
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Nav from "@/components/site/Nav";
import TransformStage from "@/components/site/TransformStage";
import Marquee from "@/components/site/Marquee";
import Modules from "@/components/site/Modules";
import HowItWorks from "@/components/site/HowItWorks";
import FinalCTA from "@/components/site/FinalCTA";

gsap.registerPlugin(ScrollTrigger);

export default function LandingPage({ onLaunchPlatform }) {
  useEffect(() => {
    // Strip a stray platform script text-node that leaks into <body> on long pages.
    document.body.childNodes.forEach((n) => {
      if (n.nodeType === 3 && n.textContent && n.textContent.includes("posthog")) {
        n.textContent = "";
      }
    });

    const lenis = new Lenis({ lerp: 0.09, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    const raf = (time) => lenis.raf(time * 1000);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(raf);
      lenis.destroy();
    };
  }, []);

  return (
    <div className="relative min-h-screen bg-[#0B1220] text-[#F4F6F9]" style={{ fontFamily: "'Inter', sans-serif" }}>
      <Nav onLaunchPlatform={onLaunchPlatform} />
      <main>
        <TransformStage onLaunchPlatform={onLaunchPlatform} />
        <Marquee />
        <Modules />
        <HowItWorks />
        <FinalCTA onLaunchPlatform={onLaunchPlatform} />
      </main>
    </div>
  );
}
