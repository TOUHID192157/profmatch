"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import {
  Check,
  Circle,
  Loader2,
  ExternalLink,
  Mail,
  X,
  ArrowUpDown,
} from "lucide-react";

interface Professor {
  id: string;
  name: string;
  university: string;
  department: string;
  email: string;
  research_areas: string;
  profile_url: string;
  match_reason: string | null;
  similarity?: number;
}

const SEARCH_STEPS = [
  "Understanding your research profile",
  "Searching university faculty",
  "Extracting professor data",
  "Calculating research similarity",
  "Ranking matches",
];

export default function MatchesPage() {
  const router = useRouter();
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [findingEmailId, setFindingEmailId] = useState<string | null>(null);
  const [selectedProfessor, setSelectedProfessor] = useState<Professor | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const stepTimer = setInterval(() => {
      setStepIndex((prev) => (prev < SEARCH_STEPS.length - 1 ? prev + 1 : prev));
    }, 3500);

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/search/matches`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Failed to find matches");
        }
        return res.json();
      })
      .then((data: Professor[]) => {
        clearInterval(stepTimer);
        setStepIndex(SEARCH_STEPS.length);
        setProfessors(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        clearInterval(stepTimer);
        setError(err.message);
        setLoading(false);
      });

    return () => clearInterval(stepTimer);
  }, [router]);

  const handleDraftEmail = async (professorId: string) => {
    setDraftingId(professorId);
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/email/draft`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ professor_id: professorId }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to draft email");
      }
      const draft = await res.json();
      router.push(`/email/${draft.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setDraftingId(null);
    }
  };

  const handleFindEmail = async (professorId: string) => {
    setFindingEmailId(professorId);
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/search/professors/${professorId}/find-email`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to find email");
      }
      const updated: Professor = await res.json();
      setProfessors((prev) =>
        prev.map((p) => (p.id === professorId ? updated : p))
      );
      if (selectedProfessor?.id === professorId) {
        setSelectedProfessor(updated);
      }
      if (!updated.email) {
        alert("No email found for this professor. Try visiting their page.");
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setFindingEmailId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
      <Sidebar />
      <main className="ml-60 px-10 py-10">
        <h1
          className="mb-8 text-3xl font-semibold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Find Professors
        </h1>

        {loading && (
          <div className="mx-auto max-w-md rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-8">
            <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-[#4DA8FF]">
              AI Research Agent working
            </p>
            <div className="space-y-4">
              {SEARCH_STEPS.map((step, i) => (
                <div key={step} className="flex items-center gap-3">
                  {i < stepIndex ? (
                    <Check size={18} className="shrink-0 text-[#4DA8FF]" />
                  ) : i === stepIndex ? (
                    <Loader2
                      size={18}
                      className="shrink-0 animate-spin text-[#4DA8FF]"
                    />
                  ) : (
                    <Circle size={18} className="shrink-0 text-[#1C2029]" />
                  )}
                  <span
                    className={`text-sm ${
                      i <= stepIndex ? "text-[#F5F6F8]" : "text-[#9AA3B2]"
                    }`}
                  >
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
            <p className="text-red-400">{error}</p>
            <Button
              variant="outline"
              className="mt-4 border-[#1C2029]"
              onClick={() => router.push("/dashboard")}
            >
              Back to Dashboard
            </Button>
          </div>
        )}

        {!loading && !error && professors.length === 0 && (
          <p className="text-[#9AA3B2]">
            No matches found. Try adding more detail to your research
            interests or bio.
          </p>
        )}

        {!loading && !error && professors.length > 0 && (
          <div className="space-y-4">
            {professors.map((prof) => (
              <div
                key={prof.id}
                onClick={() => setSelectedProfessor(prof)}
                className="cursor-pointer rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 transition hover:border-[#4DA8FF]/40"
              >
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{prof.name}</h3>
                    <p className="text-sm text-[#9AA3B2]">
                      {prof.university}
                      {prof.department ? ` · ${prof.department}` : ""}
                    </p>
                  </div>
                  {prof.similarity !== undefined && (
                    <span className="shrink-0 rounded-full bg-[#4DA8FF] px-3 py-1 font-mono text-xs font-semibold text-[#06070A]">
                      {Math.round(prof.similarity * 100)}% MATCH
                    </span>
                  )}
                </div>

                {prof.research_areas && (
                  <p className="mb-3 line-clamp-2 text-sm leading-relaxed text-[#9AA3B2]">
                    {prof.research_areas}
                  </p>
                )}

                <div className="flex items-center gap-4">
                  <p className="text-xs text-[#4DA8FF]">View details →</p>
                  {prof.profile_url && (
                    <a
                      href={prof.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs text-[#9AA3B2] hover:text-[#4DA8FF] hover:underline"
                    >
                      View Profile ↗
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {selectedProfessor && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/60"
          onClick={() => setSelectedProfessor(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="h-full w-full max-w-md overflow-y-auto border-l border-[#1C2029] bg-[#0B0D12] p-8"
          >
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-semibold">{selectedProfessor.name}</h2>
                <p className="text-sm text-[#9AA3B2]">
                  {selectedProfessor.university}
                </p>
              </div>
              <button
                onClick={() => setSelectedProfessor(null)}
                className="text-[#9AA3B2] hover:text-[#F5F6F8]"
              >
                <X size={20} />
              </button>
            </div>

            {selectedProfessor.similarity !== undefined && (
              <div className="mb-6 rounded-xl border border-[#1C2029] bg-[#06070A] p-5 text-center">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#4DA8FF]">
                  <ArrowUpDown size={12} className="mr-1 inline" />
                  Semantic similarity
                </p>
                <p
                  className="text-4xl font-semibold text-[#4DA8FF]"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {Math.round(selectedProfessor.similarity * 100)}%
                </p>
              </div>
            )}

            {selectedProfessor.department && (
              <div className="mb-5">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#9AA3B2]">
                  Department
                </p>
                <p className="text-sm">{selectedProfessor.department}</p>
              </div>
            )}

            {selectedProfessor.research_areas && (
              <div className="mb-5">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#9AA3B2]">
                  Research Areas
                </p>
                <p className="text-sm leading-relaxed">
                  {selectedProfessor.research_areas}
                </p>
              </div>
            )}

            {selectedProfessor.match_reason && (
              <div className="mb-6 rounded-lg border border-[#1C2029] bg-[#06070A] p-4">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#4DA8FF]">
                  Why You&apos;re a Match
                </p>
                <p className="text-sm">{selectedProfessor.match_reason}</p>
              </div>
            )}

            <div className="flex flex-col gap-3">
              {selectedProfessor.email ? (
                <Button
                  onClick={() => handleDraftEmail(selectedProfessor.id)}
                  disabled={draftingId === selectedProfessor.id}
                  className="bg-[#4DA8FF] text-[#06070A] hover:bg-[#6DB8FF]"
                >
                  <Mail size={16} className="mr-1.5" />
                  {draftingId === selectedProfessor.id ? "Drafting..." : "Draft Email"}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => handleFindEmail(selectedProfessor.id)}
                  disabled={findingEmailId === selectedProfessor.id}
                  className="border-[#1C2029] text-[#F5F6F8]"
                >
                  {findingEmailId === selectedProfessor.id
                    ? "Searching..."
                    : "Find Email"}
                </Button>
              )}

              {selectedProfessor.profile_url && (
                <a
                  href={selectedProfessor.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1.5 rounded-md border border-[#1C2029] py-2.5 text-sm text-[#9AA3B2] hover:text-[#4DA8FF]"
                >
                  <ExternalLink size={14} />
                  Visit Faculty Page
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}