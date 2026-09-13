import { useQuery } from "@tanstack/react-query";

import { listGarments } from "../api/client";
import GarmentCard from "../components/GarmentCard";
import Navbar from "../components/Navbar";
import WardrobeBackground from "../components/wardrobeBackground";

export default function Wardrobe() {
  const { data: garments, isLoading, isError } = useQuery({
    queryKey: ["garments"],
    queryFn: listGarments,
    // Keep polling while anything is still processing (processed_url null);
    // stop once every garment has resolved, to avoid hammering the API forever.
    refetchInterval: (query) => {
      const garments = query.state.data;
      const stillProcessing = garments?.some((g) => g.processed_url === null);
      return stillProcessing ? 3000 : false;
    },
  });

  return (
    <WardrobeBackground>
      <div className="p-6 pb-24">
        <h1 className="text-4xl font-bold text-gray-800">My Wardrobe</h1>

        <p className="text-gray-600 mt-2 mb-8">
          {garments?.length
            ? `${garments.length} item${garments.length === 1 ? "" : "s"} in your closet.`
            : "Your uploaded clothes, all in one place."}
        </p>

        {isLoading && <p className="text-gray-600">Loading your wardrobe…</p>}

        {isError && (
          <p className="text-red-500">Couldn't load your wardrobe. Try refreshing.</p>
        )}

        {garments?.length === 0 && (
          <p className="text-gray-600">
            Nothing here yet — head to Upload to add your first garment.
          </p>
        )}

        {garments && garments.length > 0 && (
          <div className="grid grid-cols-2 gap-5">
            {garments.map((garment) => (
              <GarmentCard key={garment.id} garment={garment} />
            ))}
          </div>
        )}
      </div>

      <Navbar />
    </WardrobeBackground>
  );
}
