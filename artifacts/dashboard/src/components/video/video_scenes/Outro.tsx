import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { LineChart, BarChart2 } from 'lucide-react';

export function Outro() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 3000),
      setTimeout(() => setPhase(4), 4000),
      setTimeout(() => setPhase(5), 6500), // exit to loop
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10"
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, filter: 'blur(30px)', scale: 1.5 }}
      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
    >
      <motion.div
        className="absolute inset-0 z-[-1] opacity-40 mix-blend-screen"
        style={{
          backgroundImage: `url(${import.meta.env.BASE_URL}images/dashboard-bg.png)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />

      {/* Analytics floating elements */}
      <motion.div
        className="absolute top-[20%] left-[15%] text-[#06b6d4]/50"
        initial={{ y: 50, opacity: 0 }}
        animate={phase >= 1 ? { y: 0, opacity: 1 } : { y: 50, opacity: 0 }}
        transition={{ type: 'spring' }}
      >
        <LineChart size={80} strokeWidth={1} />
      </motion.div>
      <motion.div
        className="absolute bottom-[20%] right-[15%] text-[#7c3aed]/50"
        initial={{ y: -50, opacity: 0 }}
        animate={phase >= 2 ? { y: 0, opacity: 1 } : { y: -50, opacity: 0 }}
        transition={{ type: 'spring' }}
      >
        <BarChart2 size={100} strokeWidth={1} />
      </motion.div>

      <div className="relative flex flex-col items-center text-center px-[10vw]">
        <motion.h2 
          className="text-[5vw] font-black tracking-tighter leading-none"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
        >
          Comprehensive <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#7c3aed] to-[#06b6d4]">Analytics</span>
        </motion.h2>

        <motion.p 
          className="text-[1.8vw] text-white/60 mt-6 max-w-2xl"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 3 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.2 }}
        >
          Daily snapshots. Completion charts. Top members. Total oversight of your crypto community.
        </motion.p>
        
        {/* Final Lockup */}
        <motion.div 
          className="mt-16 pt-8 border-t border-white/10 w-full max-w-md flex flex-col items-center"
          initial={{ opacity: 0, height: 0 }}
          animate={phase >= 4 ? { opacity: 1, height: 'auto' } : { opacity: 0, height: 0 }}
        >
          <div className="text-[2.5vw] font-black tracking-widest uppercase">AYZEN</div>
          <div className="text-[1vw] text-[#06b6d4] font-mono mt-1">START BUILDING TODAY</div>
        </motion.div>
      </div>
    </motion.div>
  );
}