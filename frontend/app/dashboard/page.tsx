"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface UserData {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

interface ProfileData {
  university: string | null;
  degree: string | null;
  major: string | null;
  gpa: number | null;
  graduation_year: number | null;
  research_interests: string | null;
  bio: string | null;
  skills: string[] | null;
  gre_score: number | null;
  ielts_score: number | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("Session expired. Please log in again.");
        }
        return res.json();
      })
      .then((data: UserData) => {
        setUser(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
        localStorage.removeItem("access_token");
        router.push("/login");
      });

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 404) return null;
        if (!res.ok) return null;
        return res.json();
      })
      .then((data: ProfileData | null) => {
        setProfile(data);
      })
      .catch(() => setProfile(null));
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  const profileComplete = !!(
    profile &&
    (profile.research_interests || profile.bio)
  );

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 bg-gray-50 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">
            Welcome, {user?.full_name}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-500">{user?.email}</p>

          <div className="flex flex-col gap-2">
            <Button
              onClick={() => router.push("/matches")}
              disabled={!profileComplete}
            >
              Find Matches
            </Button>
            <Button variant="outline" onClick={() => router.push("/profile")}>
              Edit My Profile
            </Button>
            <Button variant="outline" onClick={handleLogout}>
              Log Out
            </Button>
          </div>

          {!profileComplete && (
            <p className="text-xs text-amber-600">
              Add research interests or a bio to your profile to start
              finding matches.
            </p>
          )}
        </CardContent>
      </Card>

      {/* PROFILE SUMMARY */}
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">My Profile</CardTitle>
        </CardHeader>
        <CardContent>
          {!profile ? (
            <p className="text-sm text-gray-500">
              You haven&apos;t created a profile yet.{" "}
              <button
                onClick={() => router.push("/profile")}
                className="text-blue-600 underline"
              >
                Create one now
              </button>
            </p>
          ) : (
            <dl className="space-y-2 text-sm">
              <Row label="University" value={profile.university} />
              <Row label="Degree" value={profile.degree} />
              <Row label="Major" value={profile.major} />
              <Row
                label="GPA"
                value={profile.gpa != null ? String(profile.gpa) : null}
              />
              <Row
                label="Graduation Year"
                value={
                  profile.graduation_year != null
                    ? String(profile.graduation_year)
                    : null
                }
              />
              <Row
                label="GRE Score"
                value={
                  profile.gre_score != null ? String(profile.gre_score) : null
                }
              />
              <Row
                label="IELTS Score"
                value={
                  profile.ielts_score != null
                    ? String(profile.ielts_score)
                    : null
                }
              />
              <Row
                label="Research Interests"
                value={profile.research_interests}
              />
              <Row label="Bio" value={profile.bio} />
              <Row
                label="Skills"
                value={
                  profile.skills && profile.skills.length > 0
                    ? profile.skills.join(", ")
                    : null
                }
              />
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex justify-between gap-4 border-b border-gray-100 pb-1.5">
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-right text-gray-900">{value || "—"}</dd>
    </div>
  );
}