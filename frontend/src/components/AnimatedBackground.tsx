import { ReactNode, useEffect, useMemo, useState } from "react";

interface Props {
  children: ReactNode;
}

export default function AnimatedBackground({ children }: Props) {
  const [hour, setHour] = useState(new Date().getHours());

  useEffect(() => {
    const timer = setInterval(() => {
      setHour(new Date().getHours());
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  const stars = useMemo(() => {
    return Array.from({ length: 80 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      delay: Math.random() * 3,
      duration: 2 + Math.random() * 3,
      size: Math.random() * 3 + 2,
    }));
  }, []);

  let bgClass = "";
  let showClouds = false;
  let showStars = false;
  let showSun = false;
  let showMoon = false;

  if (hour >= 5 && hour < 12) {
    bgClass =
      "bg-gradient-to-b from-sky-400 via-sky-300 to-cyan-100";
    showClouds = true;
  } else if (hour >= 12 && hour < 17) {
    bgClass =
      "bg-gradient-to-b from-orange-500 via-amber-300 to-yellow-100";
    showSun = true;
    showClouds = true;
  } else if (hour >= 17 && hour < 20) {
    bgClass =
      "bg-gradient-to-b from-orange-600 via-pink-500 to-purple-800";
    showSun = true;
  } else {
    bgClass =
      "bg-gradient-to-b from-slate-950 via-blue-950 to-black";
    showStars = true;
    showMoon = true;
  }

  return (
    <div className={`relative min-h-screen overflow-hidden ${bgClass}`}>
      {/* Sun */}
      {showSun && (
        <div className="absolute top-20 right-14">
          <div className="w-24 h-24 rounded-full bg-yellow-300 animate-pulse shadow-[0_0_80px_20px_rgba(255,220,0,0.7)]" />
        </div>
      )}

      {/* Moon */}
      {showMoon && (
        <div className="absolute top-20 right-16">
          <div className="w-20 h-20 rounded-full bg-gray-100 shadow-[0_0_50px_white]" />
        </div>
      )}

      {/* Clouds */}
      {showClouds && (
        <>
          <div className="cloud top-20 left-[-250px]"></div>
          <div className="cloud top-44 left-[-400px] cloud2"></div>
          <div className="cloud top-72 left-[-300px] cloud3"></div>
        </>
      )}

      {/* Stars */}
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