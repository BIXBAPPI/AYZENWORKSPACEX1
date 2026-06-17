import { useEffect, useRef, useState } from "react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Zap, ChevronLeft, ChevronRight } from "lucide-react";

const SLIDES = [
  {
    icon: "🪂",
    title: "Complete Web3 Airdrop Tasks",
    desc: "Track every quest, submission, and requirement across all active airdrops in one place.",
  },
  {
    icon: "🏆",
    title: "Climb the Tier Ladder",
    desc: "Earn XP to rise from Bronze → Silver → Gold → Platinum and unlock exclusive rewards.",
  },
  {
    icon: "📊",
    title: "Compete on the Leaderboard",
    desc: "See your rank against community members and race to the top with every completed task.",
  },
  {
    icon: "📈",
    title: "Track Your ROI",
    desc: "Analyze your productivity, task completion rate, and estimated airdrop value over time.",
  },
];

const STATS = [
  { icon: "🔥", value: "500+", label: "Active Members" },
  { icon: "✅", value: "10,000+", label: "Tasks Completed" },
  { icon: "🪂", value: "50+", label: "Airdrop Projects" },
  { icon: "⭐", value: "$2M+", label: "XP Distributed" },
];

function AnimatedNumber({ target }: { target: string }) {
  const [display, setDisplay] = useState("0");
  const ref = useRef<HTMLSpanElement>(null);
  const animated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !animated.current) {
        animated.current = true;
        const numeric = parseInt(target.replace(/[^0-9]/g, ""), 10);
        if (isNaN(numeric)) { setDisplay(target); return; }
        const suffix = target.replace(/[0-9,]/g, "");
        let start = 0;
        const step = Math.ceil(numeric / 40);
        const timer = setInterval(() => {
          start = Math.min(start + step, numeric);
          setDisplay(start.toLocaleString() + suffix);
          if (start >= numeric) clearInterval(timer);
        }, 30);
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);

  return <span ref={ref}>{display}</span>;
}

// Particle canvas background
function StarField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let animId: number;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const stars = Array.from({ length: 120 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      speed: Math.random() * 0.3 + 0.05,
      alpha: Math.random(),
      dir: Math.random() > 0.5 ? 1 : -1,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      stars.forEach((s) => {
        s.alpha += s.dir * 0.003;
        if (s.alpha <= 0 || s.alpha >= 1) s.dir *= -1;
        s.y -= s.speed;
        if (s.y < 0) { s.y = canvas.height; s.x = Math.random() * canvas.width; }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${s.alpha * 0.7})`;
        ctx.fill();
      });
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", resize); };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />;
}

export default function Home() {
  const [slide, setSlide] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const resetTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setSlide((s) => (s + 1) % SLIDES.length), 4000);
  };

  useEffect(() => {
    resetTimer();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const prev = () => { setSlide((s) => (s - 1 + SLIDES.length) % SLIDES.length); resetTimer(); };
  const next = () => { setSlide((s) => (s + 1) % SLIDES.length); resetTimer(); };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-primary, #0a0a0f)", color: "#f1f5f9" }}>
      {/* Nav */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4"
        style={{ background: "rgba(10,10,15,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(124,58,237,0.15)" }}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-black text-lg tracking-tight" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            AYZEN WORKSPACE
          </span>
        </div>
        <div className="flex gap-2">
          <Link href="/login">
            <Button variant="ghost" className="rounded-full text-sm px-5 border" style={{ borderColor: "rgba(124,58,237,0.4)", color: "#c4b5fd" }}>
              Login
            </Button>
          </Link>
          <Link href="/register">
            <Button className="rounded-full text-sm px-5 text-white" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
              Sign Up
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative flex-1 flex flex-col items-center justify-center text-center pt-24 pb-16 min-h-screen overflow-hidden"
        style={{ background: "linear-gradient(180deg, #0a0a0f 0%, #12121a 100%)" }}>
        <StarField />
        <div className="relative z-10 max-w-3xl px-6">
          <div className="inline-block mb-4 px-3 py-1 rounded-full text-xs font-semibold" style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.4)", color: "#c4b5fd" }}>
            🚀 Web3 Community Platform — V4
          </div>
          <h1 className="text-5xl md:text-7xl font-black mb-6 leading-tight" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4,#7c3aed)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundSize: "200%" }}>
            AYZEN<br />WORKSPACE
          </h1>
          <p className="text-lg md:text-xl mb-8 max-w-xl mx-auto" style={{ color: "#94a3b8" }}>
            Web3 Airdrop Task Management — Earn XP. Complete Quests. Dominate the Leaderboard.
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link href="/register">
              <Button size="lg" className="rounded-full px-8 text-white font-bold text-base shadow-lg"
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                Get Started →
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="rounded-full px-8 font-bold text-base"
                style={{ borderColor: "rgba(124,58,237,0.5)", color: "#c4b5fd", background: "transparent" }}>
                Login
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-10" style={{ background: "#12121a", borderTop: "1px solid rgba(42,42,63,1)", borderBottom: "1px solid rgba(42,42,63,1)" }}>
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 px-6 text-center">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="text-2xl mb-1">{s.icon}</div>
              <div className="text-2xl font-black" style={{ color: "#7c3aed" }}>
                <AnimatedNumber target={s.value} />
              </div>
              <div className="text-xs mt-1" style={{ color: "#94a3b8" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Carousel */}
      <section className="py-16 px-6" style={{ background: "#0a0a0f" }}>
        <div className="max-w-2xl mx-auto">
          <h2 className="text-center text-2xl font-black mb-8" style={{ color: "#f1f5f9" }}>
            Everything you need to win airdrops
          </h2>
          <div
            className="relative rounded-2xl p-10 text-center"
            style={{ background: "#12121a", border: "1px solid rgba(124,58,237,0.2)" }}
            onMouseEnter={() => { if (timerRef.current) clearInterval(timerRef.current); }}
            onMouseLeave={resetTimer}
          >
            <div className="text-6xl mb-4">{SLIDES[slide].icon}</div>
            <h3 className="text-xl font-black mb-3" style={{ color: "#f1f5f9" }}>{SLIDES[slide].title}</h3>
            <p style={{ color: "#94a3b8" }}>{SLIDES[slide].desc}</p>

            <button onClick={prev} className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-full" style={{ background: "rgba(124,58,237,0.2)", color: "#c4b5fd" }}>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button onClick={next} className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-full" style={{ background: "rgba(124,58,237,0.2)", color: "#c4b5fd" }}>
              <ChevronRight className="w-4 h-4" />
            </button>

            <div className="flex justify-center gap-2 mt-6">
              {SLIDES.map((_, i) => (
                <button key={i} onClick={() => { setSlide(i); resetTimer(); }}
                  className="w-2 h-2 rounded-full transition-all"
                  style={{ background: i === slide ? "#7c3aed" : "rgba(124,58,237,0.3)" }} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 text-center text-xs" style={{ color: "#475569", background: "#0a0a0f", borderTop: "1px solid rgba(42,42,63,1)" }}>
        © 2025 AYZEN WORKSPACE — Web3 Community Platform
      </footer>
    </div>
  );
}
