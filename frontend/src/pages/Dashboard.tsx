import AnimatedBackground from "../components/AnimatedBackground";
import Navbar from "../components/Navbar";

export default function Dashboard() {

  const hour = new Date().getHours();

  const greeting =
    hour >= 5 && hour < 12
      ? "Good Morning ☀️"
      : hour >= 12 && hour < 17
      ? "Good Afternoon 🌞"
      : hour >= 17 && hour < 20
      ? "Good Evening 🌇"
      : "Good Night 🌙";

  return (
    <AnimatedBackground>

      <div className="p-8 pb-24">

        <h1 className="text-5xl font-bold text-white">
          {greeting}
        </h1>

        <p className="text-white/80 mt-2">
          Welcome back to StyleLoop
        </p>

        <div className="mt-12 h-[400px] rounded-3xl border-2 border-dashed border-white/40 flex justify-center items-center">

          <h2 className="text-2xl text-white">
            Outfit Recommendation Area
          </h2>

        </div>

      </div>

      <Navbar />

    </AnimatedBackground>
  );
}