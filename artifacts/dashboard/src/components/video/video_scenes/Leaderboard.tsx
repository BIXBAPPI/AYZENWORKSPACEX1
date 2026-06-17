import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Trophy, Medal, Star } from 'lucide-react';

export function Leaderboard() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 2000),
      setTimeout(() => setPhase(4), 2500),
      setTimeout(() => setPhase(5), 7000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const ranks = [
    { rank: 1, name: "CryptoWhale", xp: "12,450", tier: "Platinum", color: "from-[#e2e8f0] to-[#94a3b8]", icon: <Trophy size={20}/> },
    { rank: 2, name: "AirdropKing", xp: "10,200", tier: "Gold", color: "from-[#fcd34d] to-[#d97706]", icon: <Medal size={20}/> },
    { rank: 3, name: "DeFiNinja", xp: "8,900", tier: "Silver", color: "from-[#cbd5e1] to-[#64748b]", icon: <Star size={20}/> },
  ];

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10 px-[10vw]"
      initial={{ opacity: 0, rotateY: -90 }}
      animate={{ opacity: 1, rotateY: 0 }}
      exit={{ opacity: 0, scale: 2 }}
      transition={{ duration: 1, ease: "circOut" }}
      style={{ perspective: 1200 }}
    >
      <div className="text-center mb-12">
        <motion.h2 
          className="text-[4.5vw] font-bold"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        >
          Leaderboard & XP
        </motion.h2>
        <motion.p 
          className="text-[1.5vw] text-[#7c3aed] font-mono tracking-widest uppercase mt-2"
          initial={{ opacity: 0 }}
          animate={phase >= 1 ? { opacity: 1 } : { opacity: 0 }}
        >
          Climb the ranks. Earn rewards.
        </motion.p>
      </div>

      <div className="w-full max-w-4xl relative">
        {ranks.map((rank, i) => (
          <motion.div
            key={rank.rank}
            className="w-full bg-[#111118] border border-white/5 rounded-2xl mb-4 overflow-hidden relative"
            initial={{ opacity: 0, x: -100 }}
            animate={
              phase >= i + 2 
                ? { opacity: 1, x: 0 } 
                : { opacity: 0, x: -100 }
            }
            transition={{ type: 'spring', stiffness: 150, damping: 20 }}
          >
            {/* Rank highlight bar */}
            <div className={`absolute left-0 top-0 bottom-0 w-2 bg-gradient-to-b ${rank.color}`} />
            
            <div className="flex items-center p-6 gap-6 pl-8">
              <div className="text-[2.5vw] font-black text-white/20 w-12 text-center">
                #{rank.rank}
              </div>
              
              <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${rank.color} flex items-center justify-center text-black`}>
                {rank.icon}
              </div>
              
              <div className="flex-1">
                <div className="text-[1.5vw] font-bold text-white">{rank.name}</div>
                <div className={`text-[0.9vw] font-bold bg-clip-text text-transparent bg-gradient-to-r ${rank.color}`}>
                  {rank.tier} Tier
                </div>
              </div>
              
              <div className="text-right">
                <div className="text-[2vw] font-mono font-bold text-white">{rank.xp}</div>
                <div className="text-[1vw] text-[#7c3aed]">XP</div>
              </div>
            </div>
            
            {/* Hover sheen animation */}
            <motion.div 
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent skew-x-12"
              initial={{ x: '-100%' }}
              animate={phase >= 4 ? { x: '200%' } : { x: '-100%' }}
              transition={{ duration: 1.5, repeat: Infinity, repeatDelay: 3 }}
            />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}