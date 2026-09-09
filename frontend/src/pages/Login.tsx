import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  return (
    <div className="h-screen flex flex-col justify-center items-center">

      <h1 className="text-4xl font-bold">
        VogueVault
      </h1>

      <button
        className="mt-8 px-6 py-3 bg-amber-400 rounded-xl"
        onClick={() => navigate("/dashboard")}
      >
        Login
      </button>

    </div>
  );
}