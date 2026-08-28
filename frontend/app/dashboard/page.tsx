"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Users, TrendingUp, Target } from "lucide-react";

interface UserData {
  id: string;
  email: string;
  full_name: string;
}

interface ProfileData {
  research_interests: string | null;
  bio: string | null;
}

interface Professor {
  id: string;
  name: string;
  university: string;
  similarity?: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [topMatches, setTopMatches] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (r.ok ? r.json() : null)),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([userData, profileData]) => {
        if (!userData) {
          router.push("/login");
          return;
        }
        setUser(userData);
        setProfile(profileData);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [router]);

  const profileComplete = !!(
    profile &&
    (profile.research_interests || profile.bio)
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#06070A] text-[#9AA3B2]">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
      <Sidebar />
      <main className="ml-60 px-10 py-10">
        <h1
          className="mb-1 text-3xl font-semibold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Welcome, {user?.full_name}
        </h1>
        <p className="mb-8 text-sm text-[#9AA3B2]">{user?.email}</p>

        {!profileComplete && (
          <div className="mb-8 rounded-xl border border-[#4DA8FF]/30 bg-[#4DA8FF]/5 p-5">
            <p className="mb-3 text-sm text-[#F5F6F8]">
              Your research profile is incomplete. Add your interests to
              start finding matches.
            </p>
            <Link href="/profile">
              <Button className="bg-[#4DA8FF] text-[#06070A] hover:bg-[#6DB8FF]">
                Complete My Profile
              </Button>
            </Link>
          </div>
        )}

        {/* STAT CARDS */}
        <div className="mb-10 grid grid-cols-3 gap-4">
          <StatCard
            icon={<Users size={20} />}
            label="Professors Found"
            value={topMatches.length > 0 ? String(topMatches.length) : "—"}
          />
          <StatCard
            icon={<Target size={20} />}
            label="Top Matches"
            value={
              topMatches.filter((p) => (p.similarity ?? 0) > 0.8).length > 0
                ? String(topMatches.filter((p) => (p.similarity ?? 0) > 0.8).length)
                : "—"
            }
          />
          <StatCard
            icon={<TrendingUp size={20} />}
            label="Avg. Match"
            value={
              topMatches.length > 0
                ? Math.round(
                    (topMatches.reduce((sum, p) => sum + (p.similarity ?? 0), 0) /
                      topMatches.length) *
                      100
                  ) + "%"
                : "—"
            }
          />
        </div>

        {/* MAIN CTA */}
        <div className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-8 text-center">
          <p className="mb-2 font-mono text-xs uppercase tracking-[0.2em] text-[#4DA8FF]">
            Ready when you are
          </p>
          <h2
            className="mb-4 text-2xl font-semibold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Find your matching professors
          </h2>
          <Link href="/matches">
            <Button
              disabled={!profileComplete}
              className="bg-[#4DA8FF] px-8 text-[#06070A] hover:bg-[#6DB8FF]"
            >
              Start Search
            </Button>
          </Link>
        </div>
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-[#1C2029] bg-[#0B0D12] p-5">
      <div className="mb-3 flex items-center gap-2 text-[#4DA8FF]">
        {icon}
        <span className="font-mono text-xs uppercase tracking-wide text-[#9AA3B2]">
          {label}
        </span>
      </div>
      <p className="text-3xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>
        {value}
      </p>
    </div>
  );
}