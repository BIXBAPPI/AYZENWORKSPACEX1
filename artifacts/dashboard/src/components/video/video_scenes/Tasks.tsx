import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { CheckCircle2, ListTodo, Target } from 'lucide-react';

export function Tasks() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 1200),
      setTimeout(() => setPhase(3), 2000),
      setTimeout(() => setPhase(4), 2800),
      setTimeout(() => setPhase(5), 7000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-row items-center justify-between px-[10vw] z-10"
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '-100%', opacity: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="w-[40%] flex flex-col gap-6">
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={phase >= 1 ? { opacity: 1, x: 0 } : { opacity: 0, x: -50 }}
          transition={{ duration: 0.6 }}
          className="w-16 h-16 rounded-xl bg-[#7c3aed]/20 flex items-center justify-center text-[#7c3aed] border border-[#7c3aed]/30"
        >
          <ListTodo size={32} />
        </motion.div>

        <motion.h2 
          className="text-[4vw] font-bold leading-tight"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          Task Management
        </motion.h2>

        <motion.p 
          className="text-[1.5vw] text-white/60"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 2 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.6 }}
        >
          Create, track, and complete crypto airdrop tasks across all your projects in one unified view.
        </motion.p>
      </div>

      <div className="w-[50%] relative h-[60vh]">
        {[
          { id: 1, text: "Connect Twitter & Join Channel", project: "Project Alpha", points: 150 },
          { id: 2, text: "Perform Swap on Testnet", project: "DeFi Beta", points: 300 },
          { id: 3, text: "Stake 100 Tokens", project: "Yield Gamma", points: 500 },
        ].map((task, i) => (
          <motion.div
            key={task.id}
            className="absolute w-full bg-[#111118] border border-white/10 rounded-2xl p-6 shadow-2xl flex items-center gap-6"
            initial={{ opacity: 0, y: 100, scale: 0.8, rotateX: -20 }}
            animate={
              phase >= i + 2 
                ? { 
                    opacity: 1, 
                    y: i * 120, 
                    scale: 1, 
                    rotateX: 0,
                    zIndex: 10 - i 
                  } 
                : { opacity: 0, y: 100 + i * 20, scale: 0.8, rotateX: -20 }
            }
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          >
            <div className="w-12 h-12 rounded-full bg-[#06b6d4]/20 flex items-center justify-center text-[#06b6d4]">
              <Target size={24} />
            </div>
            <div className="flex-1">
              <div className="text-[0.9vw] text-[#7c3aed] font-mono mb-1">{task.project}</div>
              <div className="text-[1.2vw] font-medium text-white">{task.text}</div>
            </div>
            <div className="text-right">
              <div className="text-[1.5vw] font-bold text-white">+{task.points}</div>
              <div className="text-[0.8vw] text-white/50 font-mono">XP</div>
            </div>
            
            {/* Completion animation overlay */}
            <motion.div 
              className="absolute inset-0 bg-[#06b6d4]/10 rounded-2xl flex items-center justify-center backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={phase >= 4 && i === 0 ? { opacity: 1 } : { opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={phase >= 4 && i === 0 ? { scale: 1 } : { scale: 0 }}
                transition={{ type: "spring", stiffness: 300, delay: 0.2 }}
              >
                <CheckCircle2 size={64} className="text-[#06b6d4]" />
              </motion.div>
            </motion.div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}