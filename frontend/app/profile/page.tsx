"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  GraduationCap,
  FlaskConical,
  Code2,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";

interface ProfileData {
  university: string;
  degree: string;
  major: string;
  gpa: string;
  graduation_year: string;
  research_interests: string;
  bio: string;
  research_paper_links: string;
  skills: string;
  gre_score: string;
  ielts_score: string;
}

const emptyProfile: ProfileData = {
  university: "",
  degree: "",
  major: "",
  gpa: "",
  graduation_year: "",
  research_interests: "",
  bio: "",
  research_paper_links: "",
  skills: "",
  gre_score: "",
  ielts_score: "",
};

const inputClass =
  "border-[#1C2029] bg-[#06070A] text-[#F5F6F8] placeholder:text-[#5A6270] " +
  "focus-visible:ring-2 focus-visible:ring-[#4DA8FF] focus-visible:ring-offset-0 " +
  "focus-visible:border-[#4DA8FF] transition-colors";

const textareaClass =
  "w-full rounded-md border border-[#1C2029] bg-[#06070A] px-3 py-2.5 text-sm text-[#F5F6F8] " +
  "placeholder:text-[#5A6270] outline-none transition-colors resize-none " +
  "focus-visible:ring-2 focus-visible:ring-[#4DA8FF] focus-visible:border-[#4DA8FF]";

export default function ProfilePage() {
  const router = useRouter();
  const [form, setForm] = useState<ProfileData>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 404) {
          setLoading(false);
          return null;
        }
        if (!res.ok) throw new Error("Failed to load profile");
        return res.json();
      })
      .then((data) => {
        if (data) {
          setForm({
            university: data.university || "",
            degree: data.degree || "",
            major: data.major || "",
            gpa: data.gpa?.toString() || "",
            graduation_year: data.graduation_year?.toString() || "",
            research_interests: data.research_interests || "",
            bio: data.bio || "",
            research_paper_links: (data.research_paper_links || []).join(", "),
            skills: (data.skills || []).join(", "),
            gre_score: data.gre_score?.toString() || "",
            ielts_score: data.ielts_score?.toString() || "",
          });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [router]);

  const handleChange = (field: keyof ProfileData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const completion = useMemo(() => {
    const fields = Object.values(form);
    const filled = fields.filter((v) => v.trim() !== "").length;
    return Math.round((filled / fields.length) * 100);
  }, [form]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatus("idle");

    const token = localStorage.getItem("access_token");

    const payload = {
      university: form.university || null,
      degree: form.degree || null,
      major: form.major || null,
      gpa: form.gpa ? parseFloat(form.gpa) : null,
      graduation_year: form.graduation_year ? parseInt(form.graduation_year) : null,
      research_interests: form.research_interests || null,
      bio: form.bio || null,
      research_paper_links: form.research_paper_links
        ? form.research_paper_links.split(",").map((s) => s.trim())
        : [],
      skills: form.skills ? form.skills.split(",").map((s) => s.trim()) : [],
      gre_score: form.gre_score ? parseInt(form.gre_score) : null,
      ielts_score: form.ielts_score ? parseFloat(form.ielts_score) : null,
    };

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to save profile");
      setStatus("success");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
        <Sidebar />
        <main className="ml-60 flex min-h-screen items-center justify-center px-10">
          <div className="flex flex-col items-center gap-3">
            <Loader2 size={28} className="animate-spin text-[#4DA8FF]" />
            <p className="text-sm text-[#9AA3B2]">
              Loading your research profile...
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
      <Sidebar />
      <main className="ml-60 px-6 py-10 md:px-10">
        <div className="mx-auto max-w-3xl">
          {/* BREADCRUMB */}
          <p className="mb-3 font-mono text-xs uppercase tracking-[0.15em] text-[#9AA3B2]">
            Dashboard / Research Profile
          </p>

          {/* HEADER */}
          <div className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1
                className="mb-2 text-3xl font-semibold"
                style={{ fontFamily: "var(--font-display)" }}
              >
                My Research Profile
              </h1>
              <p className="text-sm text-[#9AA3B2]">
                Build your academic profile to get better professor and
                research matches.
              </p>
            </div>

            <div className="w-full shrink-0 sm:w-44">
              <div className="mb-1.5 flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wide text-[#9AA3B2]">
                  Profile Completion
                </span>
                <span className="font-mono text-xs font-semibold text-[#4DA8FF]">
                  {completion}%
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#1C2029]">
                <div
                  className="h-full rounded-full bg-[#4DA8FF] transition-all duration-500"
                  style={{ width: `${completion}%` }}
                />
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* SECTION 1 — ACADEMIC BACKGROUND */}
            <section className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 shadow-[0_1px_0_rgba(255,255,255,0.02)] sm:p-8">
              <div className="mb-6 flex items-center gap-2.5">
                <GraduationCap size={18} className="text-[#4DA8FF]" />
                <div>
                  <h2 className="text-base font-semibold">Academic Background</h2>
                  <p className="text-xs text-[#9AA3B2]">
                    Your education and academic credentials.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="university">University</Label>
                  <Input
                    id="university"
                    placeholder="e.g. University of Dhaka"
                    value={form.university}
                    onChange={(e) => handleChange("university", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="degree">Degree</Label>
                  <Input
                    id="degree"
                    placeholder="e.g. MS, PhD"
                    value={form.degree}
                    onChange={(e) => handleChange("degree", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="major">Major</Label>
                  <Input
                    id="major"
                    placeholder="e.g. Computer Science"
                    value={form.major}
                    onChange={(e) => handleChange("major", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="graduation_year">Graduation Year</Label>
                  <Input
                    id="graduation_year"
                    type="number"
                    placeholder="e.g. 2027"
                    value={form.graduation_year}
                    onChange={(e) => handleChange("graduation_year", e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="gpa">GPA</Label>
                  <Input
                    id="gpa"
                    type="number"
                    step="0.01"
                    placeholder="e.g. 3.75"
                    value={form.gpa}
                    onChange={(e) => handleChange("gpa", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gre_score">GRE Score</Label>
                  <Input
                    id="gre_score"
                    type="number"
                    placeholder="e.g. 320"
                    value={form.gre_score}
                    onChange={(e) => handleChange("gre_score", e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ielts_score">IELTS Score</Label>
                  <Input
                    id="ielts_score"
                    type="number"
                    step="0.5"
                    placeholder="e.g. 7.5"
                    value={form.ielts_score}
                    onChange={(e) => handleChange("ielts_score", e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>
            </section>

            {/* SECTION 2 — RESEARCH PROFILE */}
            <section className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 shadow-[0_1px_0_rgba(255,255,255,0.02)] sm:p-8">
              <div className="mb-6 flex items-center gap-2.5">
                <FlaskConical size={18} className="text-[#4DA8FF]" />
                <div>
                  <h2 className="text-base font-semibold">Research Profile</h2>
                  <p className="text-xs text-[#9AA3B2]">
                    Tell us what you study and what kind of research you want
                    to pursue.
                  </p>
                </div>
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="research_interests">Research Interests</Label>
                  <textarea
                    id="research_interests"
                    rows={3}
                    placeholder="Machine Learning, NLP, Computer Vision, AI Safety..."
                    value={form.research_interests}
                    onChange={(e) =>
                      handleChange("research_interests", e.target.value)
                    }
                    className={textareaClass}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <textarea
                    id="bio"
                    rows={4}
                    placeholder="Tell us about your academic background, research experience, and goals..."
                    value={form.bio}
                    onChange={(e) => handleChange("bio", e.target.value)}
                    className={textareaClass}
                  />
                </div>
              </div>
            </section>

            {/* SECTION 3 — SKILLS & PUBLICATIONS */}
            <section className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 shadow-[0_1px_0_rgba(255,255,255,0.02)] sm:p-8">
              <div className="mb-6 flex items-center gap-2.5">
                <Code2 size={18} className="text-[#4DA8FF]" />
                <div>
                  <h2 className="text-base font-semibold">
                    Skills &amp; Research Papers
                  </h2>
                </div>
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="skills">Skills</Label>
                  <Input
                    id="skills"
                    placeholder="Python, PyTorch, TensorFlow, SQL"
                    value={form.skills}
                    onChange={(e) => handleChange("skills", e.target.value)}
                    className={inputClass}
                  />
                  <p className="text-xs text-[#5A6270]">
                    Separate multiple skills with commas.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="research_paper_links">
                    Research Paper Links
                  </Label>
                  <Input
                    id="research_paper_links"
                    placeholder="https://arxiv.org/..."
                    value={form.research_paper_links}
                    onChange={(e) =>
                      handleChange("research_paper_links", e.target.value)
                    }
                    className={inputClass}
                  />
                  <p className="text-xs text-[#5A6270]">
                    Add links to papers, Google Scholar, arXiv, or
                    publications.
                  </p>
                </div>
              </div>
            </section>

            {/* STATUS ALERT */}
            {status === "success" && (
              <div className="flex items-center gap-2.5 rounded-xl border border-[#4DA8FF]/30 bg-[#4DA8FF]/5 px-4 py-3">
                <CheckCircle2 size={18} className="shrink-0 text-[#4DA8FF]" />
                <p className="text-sm text-[#F5F6F8]">
                  Profile saved successfully!
                </p>
              </div>
            )}
            {status === "error" && (
              <div className="flex items-center gap-2.5 rounded-xl border border-red-500/30 bg-red-500/5 px-4 py-3">
                <AlertCircle size={18} className="shrink-0 text-red-400" />
                <p className="text-sm text-red-300">
                  Something went wrong. Please try again.
                </p>
              </div>
            )}

            {/* FOOTER ACTIONS */}
            <div className="flex items-center gap-3 border-t border-[#1C2029] pt-6">
              <Button
                type="submit"
                disabled={saving}
                className="bg-[#4DA8FF] px-6 text-[#06070A] transition hover:bg-[#6DB8FF] disabled:opacity-60"
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin" />
                    Saving...
                  </span>
                ) : (
                  "Save Profile"
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/dashboard")}
                className="border-[#1C2029] text-[#F5F6F8] hover:bg-[#1C2029]"
              >
                Back to Dashboard
              </Button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}