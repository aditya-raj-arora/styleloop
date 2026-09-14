import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, uploadGarment } from "../api/client";
import type { Garment } from "../api/client";
import GarmentCard from "../components/GarmentCard";
import Navbar from "../components/Navbar";
import UploadBackground from "../components/uploadBackground";

export default function Upload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: uploadGarment,
    onSuccess: (garment) => {
      // Prepend into the wardrobe list cache so it's there when the user
      // navigates over, without waiting for a refetch.
      queryClient.setQueryData<Garment[]>(["garments"], (existing) =>
        existing ? [garment, ...existing] : [garment],
      );
    },
  });

  function handleFile(file: File | undefined) {
    if (!file) return;
    setPreviewUrl(URL.createObjectURL(file));
    mutation.mutate(file);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleFile(event.target.files?.[0]);
    event.target.value = ""; // allow re-selecting the same file later
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    handleFile(event.dataTransfer.files[0]);
  }

  return (
    <UploadBackground>
      <div className="p-4 sm:p-6 pb-24">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-800">Upload Garment</h1>

        <p className="text-gray-600 mt-2 mb-8">Add a new clothing item to your wardrobe.</p>

        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleInputChange}
          aria-label="Choose a garment photo"
        />

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          disabled={mutation.isPending}
          className="w-full bg-white/50 backdrop-blur-xl border-2 border-dashed border-gray-300 rounded-3xl p-8 sm:p-16 text-center shadow-xl hover:border-blue-400 transition-all duration-300 disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
        >
          <UploadCloud size={60} className="mx-auto text-blue-500" />

          <p className="mt-5 text-lg font-medium text-gray-700">
            {mutation.isPending ? "Uploading…" : "Click or Drag & Drop"}
          </p>

          <p className="text-sm text-gray-500 mt-2">JPG • PNG • WEBP</p>
        </button>

        {mutation.isError && (
          <p role="alert" className="text-red-500 mt-4">
            {mutation.error instanceof ApiError ? mutation.error.message : "Upload failed."}
          </p>
        )}

        {(mutation.isPending || mutation.isSuccess) && (
          <div className="mt-8 max-w-[240px]">
            <p className="text-sm text-gray-600 mb-2">
              {mutation.isPending ? "Uploading…" : "Added — processing in the background."}
            </p>

            {mutation.data ? (
              <GarmentCard garment={mutation.data} />
            ) : previewUrl ? (
              <div className="rounded-3xl overflow-hidden shadow-lg">
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="w-full aspect-square object-cover opacity-70"
                />
              </div>
            ) : null}
          </div>
        )}

        {mutation.isSuccess && (
          <button
            type="button"
            onClick={() => navigate("/wardrobe")}
            className="mt-4 text-blue-600 font-medium underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
          >
            View in wardrobe →
          </button>
        )}
      </div>

      <Navbar />
    </UploadBackground>
  );
}
