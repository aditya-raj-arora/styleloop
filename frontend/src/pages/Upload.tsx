import { UploadCloud } from "lucide-react";
import Navbar from "../components/Navbar";
import UploadBackground from "../components/uploadBackground";

export default function Upload() {
  return (
    <UploadBackground>

      <div className="p-6 pb-24">

        <h1 className="text-4xl font-bold text-gray-800">
          Upload Garment
        </h1>

        <p className="text-gray-600 mt-2 mb-8">
          Add a new clothing item to your wardrobe.
        </p>

        <div className="bg-white/50 backdrop-blur-xl border-2 border-dashed border-gray-300 rounded-3xl p-16 text-center shadow-xl hover:border-blue-400 transition-all duration-300">

          <UploadCloud
            size={60}
            className="mx-auto text-blue-500"
          />

          <p className="mt-5 text-lg font-medium text-gray-700">
            Click or Drag & Drop
          </p>

          <p className="text-sm text-gray-500 mt-2">
            JPG • PNG • WEBP
          </p>

        </div>

      </div>

      <Navbar />

    </UploadBackground>
  );
}