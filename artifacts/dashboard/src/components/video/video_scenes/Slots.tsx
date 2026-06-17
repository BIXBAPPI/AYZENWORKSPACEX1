import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Wallet, SplitSquareHorizontal } from 'lucide-react';

export function Slots() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 2500),
      setTimeout(() => setPhase(4), 7000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const slots = ['M1', 'M2', 'M3', 'M4', 'M5'];

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10 px-[10vw]"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ y: '-100%', opacity: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="text-center mb-16">
        <motion.div
          initial={{ opacity: 0, scale: 0 }}
          animate={phase >= 1 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0 }}
          className="inline-flex w-20 h-20 rounded-2xl bg-[#06b6d4]/20 items-center justify-center text-[#06b6d4] border border-[#06b6d4]/30 mb-6"
        >
          <SplitSquareHorizontal size={40} />
        </motion.div>
        <motion.h2 
          className="text-[4.5vw] font-bold"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        >
          Multi-Account Slots
        </motion.h2>
        <motion.p 
          className="text-[1.5vw] text-white/60 max-w-3xl mx-auto mt-4"
          initial={{ opacity: 0 }}
          animate={phase >= 2 ? { opacity: 1 } : { opacity: 0 }}
        >
          Manage multiple wallet identities per project for max airdrop farming.
        </motion.p>
      </div>

      <div className="flex gap-6 relative w-full justify-center perspective-[1000px]">
        {slots.map((slot, i) => (
          <motion.div
            key={slot}
            className="w-48 h-64 bg-gradient-to-b from-[#1a1a24] to-[#0a0a0f] rounded-2xl border border-white/10 flex flex-col items-center p-6 relative overflow-hidden group"
            initial={{ opacity: 0, rotateY: 90, z: -500 }}
            animate={
              phase >= 2 
                ? { 
                    opacity: 1, 
                    rotateY: 0, 
                    z: 0,
                    y: phase >= 3 && i === 2 ? -30 : 0, // elevate M3
                    scale: phase >= 3 && i === 2 ? 1.1 : 1,
                    borderColor: phase >= 3 && i === 2 ? 'rgba(124,58,237,0.5)' : 'rgba(255,255,255,0.1)',
                  } 
                : { opacity: 0, rotateY: 90, z: -500 }
            }
            transition={{ 
              type: 'spring', 
              stiffness: 100, 
              damping: 15, 
              delay: phase === 2 ? i * 0.1 : 0 
            }}
          >
            {/* Active glow */}
            <motion.div 
              className="absolute inset-0 bg-[#7c3aed]/20 blur-2xl"
              initial={{ opacity: 0 }}
              animate={phase >= 3 && i === 2 ? { opacity: 1 } : { opacity: 0 }}
            />

            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center text-white/50 mb-4 z-10">
              <Wallet size={28} />
            </div>
            <div className="text-[2vw] font-mono font-bold text-white z-10">{slot}</div>
            
            <motion.div 
              className="mt-auto px-4 py-1 rounded-full bg-white/5 text-[0.8vw] font-mono text-white/70 z-10"
              initial={{ opacity: 0 }}
              animate={phase >= 3 ? { opacity: 1 } : { opacity: 0 }}
              transition={{ delay: 0.5 }}
            >
              0x{Math.floor(Math.random()*9000+1000)}...
            </motion.div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}