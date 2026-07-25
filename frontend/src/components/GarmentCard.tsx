interface Props {
  image: string;
  title: string;
}

export default function GarmentCard({ image, title }: Props) {
  return (
    <div className="rounded-2xl overflow-hidden shadow-lg">
      <img
        src={image}
        alt={title}
        className="w-full h-[420px] object-cover"
      />

      <div className="p-4 bg-black text-white">
        <h2>{title}</h2>
      </div>
    </div>
  );
}