import { UploadCloud } from "lucide-react";
import Navbar from "../components/Navbar";


export default function Upload() {
  return (
    <>
      <div className="p-5">

        <h2 className="text-2xl font-bold mb-5">
          Upload Garment
        </h2>

        <div className="border-2 border-dashed rounded-2xl p-12 text-center">
          <UploadCloud size={50} className="mx-auto" />

          <p className="mt-3">
            Click here to upload clothing
          </p>
        </div>

      </div>

      <Navbar />
    </>
  );
}