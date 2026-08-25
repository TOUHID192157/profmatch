"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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

export default function MatchesPage() {
  const router = useRouter();
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [findingEmailId, setFindingEmailId] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

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
        setProfessors(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
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

      if (!updated.email) {
        alert("No email found for this professor. Try visiting their page.");
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setFindingEmailId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F5F6F3]">
        <p className="text-[#3F4A5C]">
          Analyzing your profile and searching for matches... this can take
          up to 30 seconds.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#F5F6F3]">
        <p className="text-red-500">{error}</p>
        <Button variant="outline" onClick={() => router.push("/dashboard")}>
          Back to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F5F6F3] px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-2xl font-semibold text-[#10192B]">
          Your Top Matches
        </h1>

        {professors.length === 0 && (
          <p className="text-[#3F4A5C]">
            No matches found. Try adding more detail to your research
            interests or bio.
          </p>
        )}

        <div className="space-y-4">
          {professors.map((prof) => (
            <Card key={prof.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle>{prof.name}</CardTitle>
                    <p className="text-sm text-[#3F4A5C]">
                      {prof.university}
                      {prof.department ? ` · ${prof.department}` : ""}
                    </p>
                  </div>
                  {prof.similarity !== undefined && (
                    <span className="rounded-full bg-[#E8A94A] px-3 py-1 font-mono text-xs font-medium text-[#10192B]">
                      {Math.round(prof.similarity * 100)}% match
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-4 text-sm text-[#3F4A5C]">
                  {prof.research_areas || "No research summary available."}
                </p>

                {prof.email ? (
                  <Button
                    onClick={() => handleDraftEmail(prof.id)}
                    disabled={draftingId === prof.id}
                  >
                    {draftingId === prof.id
                      ? "Drafting..."
                      : "Draft Email with AI"}
                  </Button>
                ) : (
                  <div className="rounded-lg border border-dashed border-[#D8DCE3] bg-[#FAFAFA] p-3">
                    <p className="mb-2 text-sm font-medium text-[#8A93A3]">
                      ✉️ Email not listed for this professor
                    </p>
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleFindEmail(prof.id)}
                        disabled={findingEmailId === prof.id}
                      >
                        {findingEmailId === prof.id
                          ? "Searching..."
                          : "🔍 Find Email"}
                      </Button>
                      {prof.profile_url && (
                        <a
                          href={prof.profile_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-[#3452E1] underline"
                        >
                          Visit their page →
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}