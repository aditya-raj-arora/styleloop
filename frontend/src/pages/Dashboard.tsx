import Navbar from "../components/Navbar";

export default function Dashboard() {
  return (
    <>
      <div className="p-6">
        <h1 className="text-4xl font-bold">
          VogueVault
        </h1>

        <p>Welcome to your dashboard.</p>
      </div>

      <Navbar />
    </>
  );
}