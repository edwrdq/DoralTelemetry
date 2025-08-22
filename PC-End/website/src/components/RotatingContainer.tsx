import React, { useRef, useEffect } from 'react';

interface RotatingContainerProps {
  rpm: number;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const RotatingContainer: React.FC<RotatingContainerProps> = ({
  rpm,
  children,
  className,
  style,
}) => {
  const elementRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const accumulatedRotationRef = useRef<number>(0);
  const lastUpdateTimeRef = useRef<number>(0);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const animate = (currentTime: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = currentTime;
        lastUpdateTimeRef.current = currentTime;
      }

      const deltaTime = currentTime - (lastUpdateTimeRef.current || currentTime);
      lastUpdateTimeRef.current = currentTime;

      // Calculate rotation increment based on RPM and elapsed time
      const rotationsPerMs = rpm / (60 * 1000);
      const rotationIncrement = rotationsPerMs * deltaTime * 360;

      accumulatedRotationRef.current += rotationIncrement;

      element.style.transform = `rotate(${accumulatedRotationRef.current}deg)`;

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [rpm]);

  return (
    <div ref={elementRef} className={className} style={style}>
      {children}
    </div>
  );
};
