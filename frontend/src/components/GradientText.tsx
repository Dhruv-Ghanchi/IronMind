import { useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { useMotionValue, useAnimationFrame, useTransform } from 'framer-motion';
import './GradientText.css';

interface GradientTextProps {
  children: ReactNode;
  className?: string;
  colors?: string[];
  animationSpeed?: number;
  direction?: 'horizontal' | 'vertical';
  pauseOnHover?: boolean;
}

export default function GradientText({
  children,
  className = '',
  colors = ['#5227FF', '#FF9FFC', '#B19EEF'],
  animationSpeed = 8,
  direction = 'horizontal',
  pauseOnHover = false
}: GradientTextProps) {
  const [isPaused, setIsPaused] = useState(false);
  const progress = useMotionValue(0);
  const elapsedRef = useRef(0);
  const lastTimeRef = useRef<number | null>(null);
  const spanRef = useRef<HTMLSpanElement>(null);

  const animationDuration = animationSpeed * 1000;

  useAnimationFrame((time) => {
    if (isPaused) {
      lastTimeRef.current = null;
      return;
    }

    if (lastTimeRef.current === null) {
      lastTimeRef.current = time;
      return;
    }

    const deltaTime = time - lastTimeRef.current;
    lastTimeRef.current = time;
    elapsedRef.current += deltaTime;

    const fullCycle = animationDuration * 2;
    const cycleTime = elapsedRef.current % fullCycle;

    if (cycleTime < animationDuration) {
      progress.set((cycleTime / animationDuration) * 100);
    } else {
      progress.set(100 - ((cycleTime - animationDuration) / animationDuration) * 100);
    }
  });

  useEffect(() => {
    elapsedRef.current = 0;
    progress.set(0);
  }, [animationSpeed, progress]);

  const backgroundPositionX = useTransform(progress, (p) => `${p}% 50%`);

  useEffect(() => {
    const unsubscribe = backgroundPositionX.onChange((value) => {
      if (spanRef.current) {
        spanRef.current.style.backgroundPosition = value;
      }
    });
    return unsubscribe;
  }, [backgroundPositionX]);

  const handleMouseEnter = useCallback(() => {
    if (pauseOnHover) setIsPaused(true);
  }, [pauseOnHover]);

  const handleMouseLeave = useCallback(() => {
    if (pauseOnHover) setIsPaused(false);
  }, [pauseOnHover]);

  const gradientAngle = direction === 'horizontal' ? 'to right' : 'to bottom';
  const gradientColors = [...colors, colors[0]].join(', ');

  const gradientStyle = {
    backgroundImage: `linear-gradient(${gradientAngle}, ${gradientColors})`,
    backgroundSize: direction === 'horizontal' ? '200% 100%' : '100% 200%',
    backgroundPosition: '0% 50%',
    backgroundClip: 'text' as const,
    WebkitBackgroundClip: 'text' as const,
    WebkitTextFillColor: 'transparent',
    color: 'transparent'
  };

  return (
    <span
      ref={spanRef}
      className={`animated-gradient-text ${className}`}
      style={gradientStyle}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
    </span>
  );
}
