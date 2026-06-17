import { useState, useEffect } from 'react';

// Do not modify this file as per skill instructions.
export function useVideoPlayer({ durations }: { durations: Record<string, number> }) {
  const [currentScene, setCurrentScene] = useState(0);
  const keys = Object.keys(durations);

  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).startRecording) {
      (window as any).startRecording();
    }
  }, []);

  useEffect(() => {
    const currentDuration = durations[keys[currentScene]];
    if (!currentDuration) return;

    const timer = setTimeout(() => {
      if (currentScene === keys.length - 1) {
        if (typeof window !== 'undefined' && (window as any).stopRecording) {
          (window as any).stopRecording();
        }
        setCurrentScene(0); // loop
      } else {
        setCurrentScene((prev) => prev + 1);
      }
    }, currentDuration);

    return () => clearTimeout(timer);
  }, [currentScene, durations, keys]);

  return { currentScene };
}
