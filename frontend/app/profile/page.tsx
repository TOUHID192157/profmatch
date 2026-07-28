"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

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

export default function ProfilePage() {
  const router = useRouter();
  const [form, setForm] = useState<ProfileData>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

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
          // No profile yet — that's fine, keep the form empty
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
            research_paper_links: (data.research_paper_links || []).join(
              ", "
            ),
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");

    const token = localStorage.getItem("access_token");

    const payload = {
      university: form.university || null,
      degree: form.degree || null,
      major: form.major || null,
      gpa: form.gpa ? parseFloat(form.gpa) : null,
      graduation_year: form.graduation_year
        ? parseInt(form.graduation_year)
        : null,
      research_interests: form.research_interests || null,
      bio: form.bio || null,
      research_paper_links: form.research_paper_links
        ? form.research_paper_links.split(",").map((s) => s.trim())
        : [],
      skills: form.skills
        ? form.skills.split(",").map((s) => s.trim())
        : [],
      gre_score: form.gre_score ? parseInt(form.gre_score) : null,
      ielts_score: form.ielts_score ? parseFloat(form.ielts_score) : null,
    };

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/profile`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) throw new Error("Failed to save profile");

      setMessage("Profile saved successfully!");
    } catch {
      setMessage("Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-10">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="text-2xl">My Profile</CardTitle>
          <CardDescription>
            Tell us about your academic background and research interests.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="university">University</Label>
                <Input
                  id="university"
                  value={form.university}
                  onChange={(e) =>
                    handleChange("university", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="degree">Degree</Label>
                <Input
                  id="degree"
                  placeholder="e.g. MS, PhD"
                  value={form.degree}
                  onChange={(e) => handleChange("degree", e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="major">Major</Label>
                <Input
                  id="major"
                  value={form.major}
                  onChange={(e) => handleChange("major", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="graduation_year">Graduation Year</Label>
                <Input
                  id="graduation_year"
                  type="number"
                  value={form.graduation_year}
                  onChange={(e) =>
                    handleChange("graduation_year", e.target.value)
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="gpa">GPA</Label>
                <Input
                  id="gpa"
                  type="number"
                  step="0.01"
                  value={form.gpa}
                  onChange={(e) => handleChange("gpa", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gre_score">GRE Score</Label>
                <Input
                  id="gre_score"
                  type="number"
                  value={form.gre_score}
                  onChange={(e) =>
                    handleChange("gre_score", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ielts_score">IELTS Score</Label>
                <Input
                  id="ielts_score"
                  type="number"
                  step="0.5"
                  value={form.ielts_score}
                  onChange={(e) =>
                    handleChange("ielts_score", e.target.value)
                  }
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="research_interests">Research Interests</Label>
              <Input
                id="research_interests"
                placeholder="e.g. Machine Learning, NLP"
                value={form.research_interests}
                onChange={(e) =>
                  handleChange("research_interests", e.target.value)
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="bio">Bio</Label>
              <Input
                id="bio"
                value={form.bio}
                onChange={(e) => handleChange("bio", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="skills">Skills (comma separated)</Label>
              <Input
                id="skills"
                placeholder="e.g. Python, PyTorch, SQL"
                value={form.skills}
                onChange={(e) => handleChange("skills", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="research_paper_links">
                Research Paper Links (comma separated)
              </Label>
              <Input
                id="research_paper_links"
                placeholder="https://..., https://..."
                value={form.research_paper_links}
                onChange={(e) =>
                  handleChange("research_paper_links", e.target.value)
                }
              />
            </div>

            {message && (
              <p className="text-sm text-green-600">{message}</p>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Profile"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/dashboard")}
              >
                Back to Dashboard
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}