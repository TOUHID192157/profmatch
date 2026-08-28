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
  Zap,
  Bot,
} from "lucide-react";

// ---- Shared professor shape (covers both response formats) ----
interface Professor {
  id?: string;
  name: string;
  university: string;
  department: string;
  email: string | null;
  research_areas?: string;
  research_area?: string;
  profile_url?: string;
  match_reason?: string | null;
  reason?: string;
  similarity?: number;
  relevance_score?: number;
}

interface EmailResult {
  status: string;
  professor: { name: string; email: string | null };
  email: { subject: string; body: string } | null;
  review: { approved: boolean | null; reason: string } | null;
  error: string | null;
}

interface OrchestrateResponse {
  status: string;
  professors_found?: number;
  professors?: Professor[];
  emails?: EmailResult[];
  error?: string;
}

type Mode = "quick" | "agent";

const SEARCH_STEPS_QUICK = [
  "Understanding your research profile",
  "Searching university faculty",
  "Extracting professor data",
  "Calculating research similarity",
  "Ranking matches",
];

const SEARCH_STEPS_AGENT = [
  "Understanding your research profile",
  "Agent searching university faculty",
  "Agent evaluating relevance",
  "Agent looking up missing emails",
  "Drafting personalized outreach",
];

export default function MatchesPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode | null>(null);
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [emails, setEmails] = useState<EmailResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [findingEmailId, setFindingEmailId] = useState<string | null>(null);
  const [selectedProfessor, setSelectedProfessor] = useState<Professor | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  const runSearch = (selectedMode: Mode) => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    setMode(selectedMode);
    setLoading(true);
    setError("");
    setProfessors([]);
    setEmails([]);
    setStepIndex(0);

    const steps = selectedMode === "quick" ? SEARCH_STEPS_QUICK : SEARCH_STEPS_AGENT;
    const stepTimer = setInterval(() => {
      setStepIndex((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 4000);

    const url =
      selectedMode === "quick"
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/search/matches`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/search/orchestrate`;

    const options: RequestInit =
      selectedMode === "quick"
        ? { method: "POST", headers: { Authorization: `Bearer ${token}` } }
        : {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ authorize_send: false }),
          };

    fetch(url, options)
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Failed to find matches");
        }
        return res.json();
      })
      .then((data: Professor[] | OrchestrateResponse) => {
        clearInterval(stepTimer);
        setStepIndex(steps.length);

        if (selectedMode === "quick") {
          setProfessors(data as Professor[]);
        } else {
          const orch = data as OrchestrateResponse;
          if (orch.status === "completed" || orch.status === "success") {
            setProfessors(orch.professors || []);
            setEmails(orch.emails || []);
          } else if (orch.status === "no_results") {
            setProfessors([]);
          } else {
            throw new Error(orch.error || "Research agent could not complete the search.");
          }
        }
        setLoading(false);
      })
      .catch((err: Error) => {
        clearInterval(stepTimer);
        setError(err.message);
        setLoading(false);
      });
  };

  const emailFor = (professorName: string) =>
    emails.find((e) => e.professor.name === professorName);

  const handleDraftEmail = async (professorId: string) => {
    setDraftingId(professorId);
    const token = localStorage.getItem("access_token");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/email/draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ professor_id: professorId }),
      });
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
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to find email");
      }
      const updated: Professor = await res.json();
      setProfessors((prev) =>
        prev.map((p) => (p.id === professorId ? updated : p))
      );
      if (selectedProfessor?.id === professorId) setSelectedProfessor(updated);
      if (!updated.email) {
        alert("No email found for this professor. Try visiting their page.");
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setFindingEmailId(null);
    }
  };

  const steps = mode === "quick" ? SEARCH_STEPS_QUICK : SEARCH_STEPS_AGENT;

  return (
    <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
      <Sidebar />
      <main className="ml-60 px-10 py-10">
        <h1
          className="mb-2 text-3xl font-semibold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Find Professors
        </h1>
        <p className="mb-8 text-sm text-[#9AA3B2]">
          Choose how you&apos;d like to search.
        </p>

        {/* MODE SELECTOR */}
        {!loading && (
          <div className="mb-8 grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
            <button
              onClick={() => runSearch("quick")}
              className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 text-left transition hover:border-[#4DA8FF]/40"
            >
              <Zap size={20} className="mb-3 text-[#4DA8FF]" />
              <h3 className="mb-1 font-semibold">Quick Match</h3>
              <p className="text-xs text-[#9AA3B2]">
                Fast, reliable pipeline. Ranked matches in seconds.
              </p>
            </button>

            <button
              onClick={() => runSearch("agent")}
              className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 text-left transition hover:border-[#4DA8FF]/40"
            >
              <Bot size={20} className="mb-3 text-[#4DA8FF]" />
              <h3 className="mb-1 font-semibold">AI Agent Search</h3>
              <p className="text-xs text-[#9AA3B2]">
                An autonomous agent searches, evaluates, finds emails, and
                drafts outreach. Takes 30–90s.
              </p>
            </button>
          </div>
        )}

        {loading && (
          <div className="mx-auto max-w-md rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-8">
            <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-[#4DA8FF]">
              {mode === "quick" ? "Running quick match" : "AI Research Agent working"}
            </p>
            <div className="space-y-4">
              {steps.map((step, i) => (
                <div key={step} className="flex items-center gap-3">
                  {i < stepIndex ? (
                    <Check size={18} className="shrink-0 text-[#4DA8FF]" />
                  ) : i === stepIndex ? (
                    <Loader2 size={18} className="shrink-0 animate-spin text-[#4DA8FF]" />
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
              onClick={() => setMode(null)}
            >
              Try Again
            </Button>
          </div>
        )}

        {!loading && !error && mode && professors.length === 0 && (
          <p className="text-[#9AA3B2]">
            No matches found. Try adding more detail to your research
            interests or bio.
          </p>
        )}

        {!loading && !error && professors.length > 0 && (
          <div className="space-y-4">
            {professors.map((prof, idx) => {
              const draft = mode === "agent" ? emailFor(prof.name) : null;
              return (
                <div
                  key={prof.id || idx}
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
                    {(prof.similarity !== undefined || prof.relevance_score !== undefined) && (
                      <span className="shrink-0 rounded-full bg-[#4DA8FF] px-3 py-1 font-mono text-xs font-semibold text-[#06070A]">
                        {Math.round((prof.similarity ?? prof.relevance_score ?? 0) * 100)}% MATCH
                      </span>
                    )}
                  </div>

                  {(prof.research_areas || prof.research_area) && (
                    <p className="mb-2 line-clamp-2 text-sm leading-relaxed text-[#9AA3B2]">
                      {prof.research_areas || prof.research_area}
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
                    {draft?.email && (
                      <span className="flex items-center gap-1 text-xs text-[#9AA3B2]">
                        <Mail size={12} />
                        Email drafted
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* PROFESSOR DETAILS DRAWER */}
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
                <p className="text-sm text-[#9AA3B2]">{selectedProfessor.university}</p>
              </div>
              <button
                onClick={() => setSelectedProfessor(null)}
                className="text-[#9AA3B2] hover:text-[#F5F6F8]"
              >
                <X size={20} />
              </button>
            </div>

            {(selectedProfessor.similarity !== undefined ||
              selectedProfessor.relevance_score !== undefined) && (
              <div className="mb-6 rounded-xl border border-[#1C2029] bg-[#06070A] p-5 text-center">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#4DA8FF]">
                  <ArrowUpDown size={12} className="mr-1 inline" />
                  Match score
                </p>
                <p
                  className="text-4xl font-semibold text-[#4DA8FF]"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {Math.round(
                    (selectedProfessor.similarity ?? selectedProfessor.relevance_score ?? 0) * 100
                  )}
                  %
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

            {(selectedProfessor.research_areas || selectedProfessor.research_area) && (
              <div className="mb-5">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#9AA3B2]">
                  Research Areas
                </p>
                <p className="text-sm leading-relaxed">
                  {selectedProfessor.research_areas || selectedProfessor.research_area}
                </p>
              </div>
            )}

            {(selectedProfessor.match_reason || selectedProfessor.reason) && (
              <div className="mb-6 rounded-lg border border-[#1C2029] bg-[#06070A] p-4">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-[#4DA8FF]">
                  Why You&apos;re a Match
                </p>
                <p className="text-sm">
                  {selectedProfessor.match_reason || selectedProfessor.reason}
                </p>
              </div>
            )}

            {/* Quick mode actions */}
            {mode === "quick" && selectedProfessor.id && (
              <div className="flex flex-col gap-3">
                {selectedProfessor.email ? (
                  <Button
                    onClick={() => handleDraftEmail(selectedProfessor.id!)}
                    disabled={draftingId === selectedProfessor.id}
                    className="bg-[#4DA8FF] text-[#06070A] hover:bg-[#6DB8FF]"
                  >
                    <Mail size={16} className="mr-1.5" />
                    {draftingId === selectedProfessor.id ? "Drafting..." : "Draft Email"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => handleFindEmail(selectedProfessor.id!)}
                    disabled={findingEmailId === selectedProfessor.id}
                    className="border-[#1C2029] text-[#F5F6F8]"
                  >
                    {findingEmailId === selectedProfessor.id ? "Searching..." : "Find Email"}
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
            )}

            {/* Agent mode: show drafted email directly */}
            {mode === "agent" &&
              (() => {
                const draft = emailFor(selectedProfessor.name);
                if (!draft?.email) {
                  return (
                    <p className="text-sm text-[#9AA3B2]">
                      No email draft was generated for this professor in this run.
                    </p>
                  );
                }
                return (
                  <div className="rounded-lg border border-[#1C2029] bg-[#06070A] p-4">
                    <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-[#4DA8FF]">
                      Drafted Outreach Email
                    </p>
                    <p className="mb-2 text-sm font-medium">{draft.email.subject}</p>
                    <p className="whitespace-pre-line text-xs leading-relaxed text-[#9AA3B2]">
                      {draft.email.body}
                    </p>
                  </div>
                );
              })()}
          </div>
        </div>
      )}
    </div>
  );
}