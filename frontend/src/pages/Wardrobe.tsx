import Navbar from "../components/Navbar";

const clothes = [
  "https://picsum.photos/300?1",
  "https://picsum.photos/300?2",
  "https://picsum.photos/300?3",
  "https://picsum.photos/300?4",
];

export default function Wardrobe() {
  return (
    <>
      <div className="p-5">

        <h2 className="text-2xl font-bold mb-5">
          My Wardrobe
        </h2>

        <div className="grid grid-cols-2 gap-4">
          {clothes.map((item, index) => (
            <img
              key={index}
              src={item}
              className="rounded-xl aspect-square object-cover"
            />
          ))}
        </div>

      </div>

      <Navbar />
    </>
  );
}