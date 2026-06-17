import { motion, AnimatePresence } from 'framer-motion';
import { useVideoPlayer } from '@/lib/video/hooks';
import { Open } from './video_scenes/Open';
import { Tasks } from './video_scenes/Tasks';
import { Slots } from './video_scenes/Slots';
import { Telegram } from './video_scenes/Telegram';
import { Leaderboard } from './video_scenes/Leaderboard';
import { Outro } from './video_scenes/Outro';

const SCENE_DURATIONS = { 
  open: 6000, 
  tasks: 8000, 
  slots: 8000, 
  telegram: 8000, 
  leaderboard: 8000, 
  outro: 7000 
};

// Scene persistence properties
const persistentPos = [
  { x: '50vw', y: '50vh', scale: 1.5, opacity: 0.1 }, // open
  { x: '20vw', y: '20vh', scale: 0.8, opacity: 0.3 }, // tasks
  { x: '80vw', y: '70vh', scale: 1.2, opacity: 0.2 }, // slots
  { x: '10vw', y: '80vh', scale: 1.0, opacity: 0.4 }, // telegram
  { x: '70vw', y: '20vh', scale: 0.9, opacity: 0.2 }, // leaderboard
  { x: '50vw', y: '50vh', scale: 1.8, opacity: 0.1 }, // outro
];

export default function VideoTemplate() {
  const { currentScene } = useVideoPlayer({ durations: SCENE_DURATIONS });

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#0a0a0f]">
      {/* Persistent Background Layer */}
      <div className="absolute inset-0 z-0">
        <motion.div 
          className="absolute w-[800px] h-[800px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, #7c3aed, transparent 70%)' }}
          animate={{
            x: ['-20%', '50%', '-10%'],
            y: ['-20%', '30%', '50%'],
            scale: [1, 1.2, 0.8],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div 
          className="absolute w-[600px] h-[600px] rounded-full blur-[100px]"
          style={{ background: 'radial-gradient(circle, #06b6d4, transparent 70%)' }}
          animate={{
            x: ['60%', '-10%', '70%'],
            y: ['60%', '10%', '-20%'],
            scale: [0.8, 1.3, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }}
        />
        
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:4vw_4vw] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_80%)]" />
      </div>

      {/* Persistent Midground Accent */}
      <motion.div
        className="absolute w-[30vw] h-[30vw] border border-[#7c3aed]/20 rounded-full z-0 pointer-events-none"
        animate={{
          x: persistentPos[currentScene].x,
          y: persistentPos[currentScene].y,
          scale: persistentPos[currentScene].scale,
          opacity: persistentPos[currentScene].opacity,
        }}
        style={{ transform: 'translate(-50%, -50%)' }}
        transition={{ duration: 2.5, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.div
        className="absolute w-[40vw] h-[40vw] border border-[#06b6d4]/10 rounded-full z-0 pointer-events-none"
        animate={{
          x: persistentPos[currentScene].x,
          y: persistentPos[currentScene].y,
          scale: persistentPos[currentScene].scale * 1.5,
          opacity: persistentPos[currentScene].opacity * 0.5,
        }}
        style={{ transform: 'translate(-50%, -50%)' }}
        transition={{ duration: 3, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* Foreground Content */}
      <AnimatePresence mode="popLayout">
        {currentScene === 0 && <Open key="open" />}
        {currentScene === 1 && <Tasks key="tasks" />}
        {currentScene === 2 && <Slots key="slots" />}
        {currentScene === 3 && <Telegram key="telegram" />}
        {currentScene === 4 && <Leaderboard key="leaderboard" />}
        {currentScene === 5 && <Outro key="outro" />}
      </AnimatePresence>
    </div>
  );
}