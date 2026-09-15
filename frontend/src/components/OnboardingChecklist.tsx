import { Link } from "react-router-dom";

import type { Garment } from "../api/client";

interface OnboardingChecklistProps {
  garments: Garment[] | undefined;
  garmentsLoading: boolean;
  hasBasePhoto: boolean;
}

// A garment the rotation engine can actually place in an outfit: clean and
// tagged (category set — see backend/app/routers/outfits.py::_clean_scoring_garments).
function isUsable(g: Garment): boolean {
  return g.state === "clean" && g.category !== null;
}

// Mirrors rotation._base_combinations: a complete outfit needs a top+bottom
// pair, or a dress, among the usable garments.
function hasCompleteOutfit(garments: Garment[]): boolean {
  const usable = garments.filter(isUsable);
  const hasTop = usable.some((g) => g.category === "top");
  const hasBottom = usable.some((g) => g.category === "bottom");
  const hasDress = usable.some((g) => g.category === "dress");
  return (hasTop && hasBottom) || hasDress;
}

/**
 * First-run checklist shown on the Dashboard until a user has enough
 * tagged, clean garments to generate an outfit — replaces handing a brand
 * new signup a bare "No outfit yet" message with concrete next steps.
 */
export default function OnboardingChecklist({
  garments,
  garmentsLoading,
  hasBasePhoto,
}: OnboardingChecklistProps) {
  const list = garments ?? [];
  const uploaded = list.length > 0;
  const tagging = list.some((g) => g.category === null);
  const outfitReady = hasCompleteOutfit(list);

  const steps = [
    {
      label: "Upload a few garments",
      done: uploaded,
      detail: garmentsLoading
        ? undefined
        : uploaded
        ? `${list.length} uploaded`
        : "Photos of what's in your closet",
      cta: !uploaded ? (
        <Link
          to="/upload"
          className="text-amber-300 font-medium underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-white rounded"
        >
          Upload garments →
        </Link>
      ) : undefined,
    },
    {
      label: "Wait for auto-tagging",
      done: uploaded && !tagging,
      detail:
        uploaded && tagging
          ? "Still processing — hang tight, this takes a few seconds"
          : undefined,
    },
    {
      label: "Have a top + bottom, or a dress",
      done: outfitReady,
      detail: !outfitReady
        ? "So the engine has a complete outfit to suggest"
        : undefined,
      cta:
        uploaded && !tagging && !outfitReady ? (
          <Link
            to="/upload"
            className="text-amber-300 font-medium underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-white rounded"
          >
            Upload more →
          </Link>
        ) : undefined,
    },
    {
      label: "Add a photo of yourself (optional)",
      done: hasBasePhoto,
      detail: !hasBasePhoto ? "Needed later to try outfits on" : undefined,
    },
  ];

  return (
    <div className="w-full max-w-xs text-left">
      <h2 className="text-2xl text-white text-center mb-1">Let's get you set up</h2>
      <p className="text-white/60 text-sm text-center mb-5">
        A few steps before your first daily outfit.
      </p>
      <ol className="space-y-3">
        {steps.map((step) => (
          <li key={step.label} className="flex items-start gap-3">
            <span
              aria-hidden="true"
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs ${
                step.done
                  ? "bg-green-500 text-white"
                  : "bg-white/15 text-white/50 border border-white/30"
              }`}
            >
              {step.done ? "✓" : ""}
            </span>
            <div>
              <p className={step.done ? "text-white/60 line-through" : "text-white"}>
                {step.label}
              </p>
              {step.detail && <p className="text-white/50 text-xs mt-0.5">{step.detail}</p>}
              {step.cta && <div className="text-sm mt-0.5">{step.cta}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
