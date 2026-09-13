import AnimatedBackground from "../components/AnimatedBackground";
import Navbar from "../components/Navbar";
import type { Outfit } from "../api/client";

// Mock "today's outfit" shaped against the real Outfit contract (see
// api/client.ts) so swapping in GET /outfits/daily later (Sprint 2) is a
// data-source change, not a type rework.
const _MOCK_DAILY_OUTFIT: Outfit = {
  id: 1,
  user_id: 1,
  garment_ids: [101, 102, 103],
  score: 2.4,
  generated_for: new Date().toISOString().slice(0, 10),
  created_at: new Date().toISOString(),
};

export default function Dashboard() {
  const dailyOutfit = _MOCK_DAILY_OUTFIT;

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

        <div className="mt-12 h-[400px] rounded-3xl border-2 border-dashed border-white/40 flex flex-col justify-center items-center gap-2">

          <h2 className="text-2xl text-white">
            Outfit Recommendation Area
          </h2>

          <p className="text-white/60 text-sm">
            {dailyOutfit.garment_ids.length} items · mock score {dailyOutfit.score}
          </p>

        </div>

      </div>

      <Navbar />

    </AnimatedBackground>
  );
}