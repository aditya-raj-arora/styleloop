import { useState } from "react";
import GarmentCard from "../components/GarmentCard";
import Navbar from "../components/Navbar";

const outfits = [
  {
    image: "https://picsum.photos/500/700?1",
    title: "Summer Fit"
  },
  {
    image: "https://picsum.photos/500/700?2",
    title: "Streetwear"
  },
  {
    image: "https://picsum.photos/500/700?3",
    title: "Formal"
  }
];

export default function Swipe() {
  const [index, setIndex] = useState(0);

  function next() {
    setIndex((index + 1) % outfits.length);
  }

  return (
    <>
      <div className="p-5">
        <GarmentCard
          image={outfits[index].image}
          title={outfits[index].title}
        />

        <div className="flex justify-center gap-5 mt-6">
          <button
            onClick={next}
            className="bg-red-500 px-6 py-2 rounded"
          >
            Skip
          </button>

          <button
            onClick={next}
            className="bg-green-500 px-6 py-2 rounded"
          >
            Like
          </button>
        </div>
      </div>

      <Navbar />
    </>
  );
}