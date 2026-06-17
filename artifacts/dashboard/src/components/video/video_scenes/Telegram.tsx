import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { MessageCircle, Zap } from 'lucide-react';

export function Telegram() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1200),
      setTimeout(() => setPhase(3), 2000),
      setTimeout(() => setPhase(4), 3000),
      setTimeout(() => setPhase(5), 4000),
      setTimeout(() => setPhase(6), 7000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-row items-center justify-between px-[10vw] z-10"
      initial={{ scale: 1.5, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ opacity: 0, filter: 'blur(20px)' }}
      transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
    >
      <motion.div
        className="absolute inset-0 z-[-1] opacity-30 mix-blend-screen"
        style={{
          backgroundImage: `url(${import.meta.env.BASE_URL}images/bot-bg.png)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />

      <div className="w-[45%] relative h-[70vh] flex justify-center items-center">
        {/* Phone mockup */}
        <motion.div 
          className="w-72 h-[36rem] bg-black border-4 border-white/20 rounded-[3rem] overflow-hidden relative shadow-[0_0_100px_rgba(6,182,212,0.2)]"
          initial={{ y: 100, opacity: 0, rotate: -10 }}
          animate={phase >= 1 ? { y: 0, opacity: 1, rotate: 0 } : { y: 100, opacity: 0, rotate: -10 }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        >
          {/* Header */}
          <div className="bg-[#1a1a24] p-4 flex items-center gap-3 border-b border-white/10">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#7c3aed] to-[#06b6d4] flex items-center justify-center">
              <Zap size={20} className="text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">AYZEN Bot</div>
              <div className="text-xs text-[#06b6d4]">bot</div>
            </div>
          </div>

          {/* Chat area */}
          <div className="p-4 flex flex-col gap-4">
            <motion.div 
              className="bg-[#2b5278] text-white p-3 rounded-2xl rounded-br-sm self-end max-w-[80%]"
              initial={{ opacity: 0, scale: 0.8, x: 20 }}
              animate={phase >= 2 ? { opacity: 1, scale: 1, x: 0 } : { opacity: 0, scale: 0.8, x: 20 }}
            >
              /submit_task
            </motion.div>
            
            <motion.div 
              className="bg-[#1a1a24] text-white p-3 rounded-2xl rounded-bl-sm self-start max-w-[90%] border border-white/10"
              initial={{ opacity: 0, scale: 0.8, x: -20 }}
              animate={phase >= 3 ? { opacity: 1, scale: 1, x: 0 } : { opacity: 0, scale: 0.8, x: -20 }}
            >
              Select project for submission:
              <div className="grid grid-cols-1 gap-2 mt-3">
                <div className="bg-white/10 p-2 rounded text-center text-sm cursor-pointer hover:bg-white/20">Project Alpha</div>
                <div className="bg-white/10 p-2 rounded text-center text-sm cursor-pointer hover:bg-white/20">DeFi Beta</div>
              </div>
            </motion.div>

            <motion.div 
              className="bg-[#2b5278] text-white p-3 rounded-2xl rounded-br-sm self-end max-w-[80%]"
              initial={{ opacity: 0, scale: 0.8, x: 20 }}
              animate={phase >= 4 ? { opacity: 1, scale: 1, x: 0 } : { opacity: 0, scale: 0.8, x: 20 }}
            >
              Project Alpha
            </motion.div>

            <motion.div 
              className="bg-[#1a1a24] text-white p-3 rounded-2xl rounded-bl-sm self-start max-w-[90%] border border-[#06b6d4]/30 bg-[#06b6d4]/10"
              initial={{ opacity: 0, scale: 0.8, x: -20 }}
              animate={phase >= 5 ? { opacity: 1, scale: 1, x: 0 } : { opacity: 0, scale: 0.8, x: -20 }}
            >
              ✅ Task submitted successfully! <br/>
              +150 XP awarded.
            </motion.div>
          </div>
        </motion.div>
      </div>

      <div className="w-[45%] flex flex-col gap-6 text-right items-end">
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={phase >= 1 ? { opacity: 1, x: 0 } : { opacity: 0, x: 50 }}
          transition={{ duration: 0.6 }}
          className="w-20 h-20 rounded-2xl bg-[#06b6d4]/20 flex items-center justify-center text-[#06b6d4] border border-[#06b6d4]/30"
        >
          <MessageCircle size={40} />
        </motion.div>

        <motion.h2 
          className="text-[4.5vw] font-bold leading-tight"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        >
          Native Telegram <br/><span className="text-[#06b6d4]">Integration</span>
        </motion.h2>

        <motion.p 
          className="text-[1.6vw] text-white/60 max-w-xl"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 2 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        >
          Submit tasks, manage community, and track progress directly from Telegram. Seamless sync with the dashboard.
        </motion.p>
      </div>
    </motion.div>
  );
}