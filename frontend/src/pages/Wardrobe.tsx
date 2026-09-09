import { useState } from "react";
import { Heart } from "lucide-react";
import Navbar from "../components/Navbar";
import WardrobeBackground from "../components/wardrobeBackground";

const clothes = [
  {
    id: 1,
    image: "https://picsum.photos/300?1",
    favourite: false,
  },
  {
    id: 2,
    image: "https://picsum.photos/300?2",
    favourite: false,
  },
  {
    id: 3,
    image: "https://picsum.photos/300?3",
    favourite: false,
  },
  {
    id: 4,
    image: "https://picsum.photos/300?4",
    favourite: false,
  },
];

export default function Wardrobe() {
  const [items, setItems] = useState(clothes);

  const toggleFavourite = (id: number) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? { ...item, favourite: !item.favourite }
          : item
      )
    );
  };

  return (
    <WardrobeBackground>
      <div className="p-6 pb-24">

        <h1 className="text-4xl font-bold text-gray-800">
          My Wardrobe
        </h1>

        <p className="text-gray-600 mt-2 mb-8">
          Your favorite outfits, all in one place.
        </p>

        <div className="grid grid-cols-2 gap-5">

          {items.map((item) => (

            <div
              key={item.id}
              className="relative rounded-3xl overflow-hidden bg-white/30 backdrop-blur-xl border border-white/30 shadow-lg transition-all duration-300 hover:scale-105"
            >

              {/* Heart Button */}

              <button
                onClick={() => toggleFavourite(item.id)}
                className="absolute top-3 right-3 z-20 bg-white/80 backdrop-blur-md rounded-full p-2 hover:scale-110 transition"
              >

                <Heart
                  size={22}
                  className={`transition-all ${
                    item.favourite
                      ? "fill-red-500 text-red-500"
                      : "text-gray-600"
                  }`}
                />

              </button>

              <img
                src={item.image}
                alt="Clothing"
                className="w-full aspect-square object-cover"
              />

            </div>

          ))}

        </div>

      </div>

      <Navbar />

    </WardrobeBackground>
  );
}