import { ReactNode, useEffect, useMemo, useState } from "react";

interface Props {
  children: ReactNode;
}

export default function WardrobeBackground({ children }: Props) {
  const [hour, setHour] = useState(new Date().getHours());

  useEffect(() => {
    const timer = setInterval(() => {
      setHour(new Date().getHours());
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  const stars = useMemo(() => {
    return Array.from({ length: 35 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 4,
      duration: 2 + Math.random() * 3,
      size: Math.random() * 2 + 1,
    }));
  }, []);

  let bg = "";
  let showClouds = false;
  let showSun = false;
  let showMoon = false;
  let showStars = false;

  if (hour >= 5 && hour < 12) {
    bg =
      "bg-gradient-to-b from-sky-100 via-blue-50 to-white";
    showClouds = true;
  } else if (hour >= 12 && hour < 17) {
    bg =
      "bg-gradient-to-b from-orange-100 via-yellow-50 to-white";
    showClouds = true;
    showSun = true;
  } else if (hour >= 17 && hour < 20) {
    bg =
      "bg-gradient-to-b from-orange-100 via-pink-100 to-purple-100";
    showSun = true;
  } else {
    bg =
      "bg-gradient-to-b from-slate-800 via-slate-700 to-slate-600";
    showMoon = true;
    showStars = true;
  }

  return (
    <div className={`relative min-h-screen overflow-hidden ${bg}`}>
      {showSun && (
        <div className="absolute top-12 right-12 w-20 h-20 rounded-full bg-yellow-300 opacity-60 blur-sm" />
      )}

      {showMoon && (
        <div className="absolute top-12 right-12 w-16 h-16 rounded-full bg-white opacity-80 shadow-[0_0_30px_white]" />
      )}

      {showClouds && (
        <>
          <div className="cloud opacity-40 top-16 left-[-200px]" />
          <div className="cloud cloud2 opacity-30 top-40 left-[-350px]" />
        </>
      )}

      {showStars &&
        stars.map((star) => (
          <div
            key={star.id}
            className="star"
            style={{
              left: `${star.left}%`,
              top: `${star.top}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              animationDelay: `${star.delay}s`,
              animationDuration: `${star.duration}s`,
            }}
          />
        ))}

      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}