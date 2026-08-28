"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, CheckCircle2, Loader2, ArrowLeft } from "lucide-react";

interface EmailDraft {
  id: string;
  professor_name: string;
  professor_email: string | null;
  subject: string;
  body: string;
  status: string;
  sent_at: string | null;
  created_at: string;
}

const inputClass =
  "border-[#1C2029] bg-[#06070A] text-[#F5F6F8] placeholder:text-[#5A6270] " +
  "focus-visible:ring-2 focus-visible:ring-[#4DA8FF] focus-visible:border-[#4DA8FF]";

export default function EmailDraftPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [draft, setDraft] = useState<EmailDraft | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/email/drafts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((drafts: EmailDraft[]) => {
        const found = drafts.find((d) => d.id === id);
        if (found) {
          setDraft(found);
          setSubject(found.subject);
          setBody(found.body);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id, router]);

  const handleSend = async () => {
    if (!draft) return;
    setSending(true);
    setMessage("");
    const token = localStorage.getItem("access_token");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/email/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ draft_id: draft.id }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to send email");
      }

      setMessage("Email sent successfully!");
      setDraft((prev) => (prev ? { ...prev, status: "sent" } : prev));
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
        <Sidebar />
        <main className="ml-60 flex min-h-screen items-center justify-center px-10">
          <div className="flex flex-col items-center gap-3">
            <Loader2 size={28} className="animate-spin text-[#4DA8FF]" />
            <p className="text-sm text-[#9AA3B2]">Loading draft...</p>
          </div>
        </main>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
        <Sidebar />
        <main className="ml-60 flex min-h-screen flex-col items-center justify-center gap-4 px-10">
          <p className="text-[#9AA3B2]">Draft not found.</p>
          <Button
            variant="outline"
            onClick={() => router.push("/matches")}
            className="border-[#1C2029] text-[#F5F6F8]"
          >
            Back to Matches
          </Button>
        </main>
      </div>
    );
  }

  const alreadySent = draft.status === "sent";

  return (
    <div className="min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]">
      <Sidebar />
      <main className="ml-60 px-6 py-10 md:px-10">
        <div className="mx-auto max-w-2xl">
          <button
            onClick={() => router.push("/matches")}
            className="mb-6 flex items-center gap-1.5 text-sm text-[#9AA3B2] hover:text-[#4DA8FF]"
          >
            <ArrowLeft size={16} />
            Back to Matches
          </button>

          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#4DA8FF]/10">
              <Mail size={18} className="text-[#4DA8FF]" />
            </div>
            <div>
              <h1
                className="text-2xl font-semibold"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {draft.professor_name}
              </h1>
              <p className="text-sm text-[#9AA3B2]">
                {draft.professor_email || "No email address on file"}
              </p>
            </div>
          </div>

          <div className="space-y-6 rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 sm:p-8">
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                disabled={alreadySent}
                className={inputClass}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="body">Body</Label>
              <textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={alreadySent}
                rows={14}
                className="w-full rounded-md border border-[#1C2029] bg-[#06070A] px-3 py-2.5 text-sm leading-relaxed text-[#F5F6F8] outline-none transition-colors focus-visible:border-[#4DA8FF] focus-visible:ring-2 focus-visible:ring-[#4DA8FF] disabled:opacity-60"
              />
            </div>

            {message && (
              <div
                className={`flex items-center gap-2.5 rounded-xl px-4 py-3 ${
                  message.includes("success")
                    ? "border border-[#4DA8FF]/30 bg-[#4DA8FF]/5"
                    : "border border-red-500/30 bg-red-500/5"
                }`}
              >
                {message.includes("success") && (
                  <CheckCircle2 size={18} className="shrink-0 text-[#4DA8FF]" />
                )}
                <p
                  className={
                    message.includes("success") ? "text-sm text-[#F5F6F8]" : "text-sm text-red-300"
                  }
                >
                  {message}
                </p>
              </div>
            )}

            <div className="flex items-center gap-3 border-t border-[#1C2029] pt-6">
              {alreadySent ? (
                <p className="flex items-center gap-2 text-sm font-medium text-[#4DA8FF]">
                  <CheckCircle2 size={16} />
                  This email has been sent
                </p>
              ) : (
                <Button
                  onClick={handleSend}
                  disabled={sending || !draft.professor_email}
                  className="bg-[#4DA8FF] px-6 text-[#06070A] hover:bg-[#6DB8FF] disabled:opacity-60"
                >
                  {sending ? (
                    <span className="flex items-center gap-2">
                      <Loader2 size={14} className="animate-spin" />
                      Sending...
                    </span>
                  ) : (
                    "Send Email"
                  )}
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => router.push("/matches")}
                className="border-[#1C2029] text-[#F5F6F8] hover:bg-[#1C2029]"
              >
                Back to Matches
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}