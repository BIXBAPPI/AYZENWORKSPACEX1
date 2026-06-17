import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Open() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 2500),
      setTimeout(() => setPhase(4), 5000), // exit
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10"
      initial={{ opacity: 0, scale: 1.1 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, filter: 'blur(20px)' }}
      transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
    >
      <motion.div
        className="absolute inset-0 z-[-1] opacity-40 mix-blend-overlay"
        style={{
          backgroundImage: `url(${import.meta.env.BASE_URL}images/crypto-bg.png)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />

      <div className="relative flex flex-col items-center text-center">
        {/* Logo/Icon */}
        <motion.div
          initial={{ opacity: 0, y: 50, rotateX: 90 }}
          animate={phase >= 1 ? { opacity: 1, y: 0, rotateX: 0 } : { opacity: 0, y: 50, rotateX: 90 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          className="w-24 h-24 mb-8 bg-gradient-to-br from-[#7c3aed] to-[#06b6d4] rounded-2xl flex items-center justify-center shadow-[0_0_50px_rgba(124,58,237,0.5)]"
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinelinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5Z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </motion.div>

        {/* Title */}
        <h1 className="text-[8vw] font-black tracking-tighter leading-none" style={{ fontFamily: 'var(--font-sans)' }}>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70">AYZEN</span>
        </h1>

        {/* Tagline */}
        <div className="mt-6 overflow-hidden">
          <motion.p 
            initial={{ y: "100%", opacity: 0 }}
            animate={phase >= 2 ? { y: "0%", opacity: 1 } : { y: "100%", opacity: 0 }}
            transition={{ type: 'spring', stiffness: 150, damping: 25 }}
            className="text-[2vw] text-[#06b6d4] font-medium tracking-wide uppercase"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Mission Control
          </motion.p>
        </div>
        
        <div className="mt-2 overflow-hidden">
          <motion.p 
            initial={{ y: "-100%", opacity: 0 }}
            animate={phase >= 3 ? { y: "0%", opacity: 1 } : { y: "-100%", opacity: 0 }}
            transition={{ type: 'spring', stiffness: 150, damping: 25 }}
            className="text-[1.8vw] text-white/60 font-light"
          >
            For Crypto Communities
          </motion.p>
        </div>
      </div>
    </motion.div>
  );
}