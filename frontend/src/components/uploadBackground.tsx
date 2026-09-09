import { ReactNode, useEffect, useMemo, useState } from "react";

interface Props {
  children: ReactNode;
}

export default function UploadBackground({ children }: Props) {
  const [hour, setHour] = useState(new Date().getHours());

  useEffect(() => {
    const timer = setInterval(() => {
      setHour(new Date().getHours());
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  const bubbles = useMemo(() => {
    return Array.from({ length: 18 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 60 + Math.random() * 80,
      duration: 8 + Math.random() * 8,
      delay: Math.random() * 5,
    }));
  }, []);

  let bg = "";
  let accent = "";

  if (hour >= 5 && hour < 12) {
    bg = "bg-gradient-to-br from-sky-50 via-cyan-50 to-white";
    accent = "bg-sky-300/20";
  } else if (hour >= 12 && hour < 17) {
    bg = "bg-gradient-to-br from-orange-50 via-yellow-50 to-white";
    accent = "bg-yellow-300/20";
  } else if (hour >= 17 && hour < 20) {
    bg = "bg-gradient-to-br from-pink-50 via-orange-50 to-purple-50";
    accent = "bg-pink-300/20";
  } else {
    bg = "bg-gradient-to-br from-slate-200 via-slate-100 to-white";
    accent = "bg-indigo-300/15";
  }

  return (
    <div className={`relative min-h-screen overflow-hidden ${bg}`}>
      {bubbles.map((bubble) => (
        <div
          key={bubble.id}
          className={`absolute rounded-full blur-3xl animate-float ${accent}`}
          style={{
            left: `${bubble.left}%`,
            top: `${bubble.top}%`,
            width: bubble.size,
            height: bubble.size,
            animationDuration: `${bubble.duration}s`,
            animationDelay: `${bubble.delay}s`,
          }}
        />
      ))}

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}