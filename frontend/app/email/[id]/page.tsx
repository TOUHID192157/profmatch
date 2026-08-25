"use client";

import { useEffect, useState, use } from "react";
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
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/email/send`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ draft_id: draft.id }),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to send email");
      }

      setMessage("Email sent successfully! ✓");
      setDraft((prev) => (prev ? { ...prev, status: "sent" } : prev));
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F5F6F3]">
        <p className="text-[#3F4A5C]">Loading...</p>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#F5F6F3]">
        <p className="text-[#3F4A5C]">Draft not found.</p>
        <Button variant="outline" onClick={() => router.push("/matches")}>
          Back to Matches
        </Button>
      </div>
    );
  }

  const alreadySent = draft.status === "sent";

  return (
    <div className="min-h-screen bg-[#F5F6F3] px-6 py-10">
      <div className="mx-auto max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Email to {draft.professor_name}</CardTitle>
            <CardDescription>
              {draft.professor_email || "No email address on file"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                disabled={alreadySent}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="body">Body</Label>
              <textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={alreadySent}
                rows={12}
                className="w-full rounded-md border border-[#D8DCE3] bg-white p-3 text-sm"
              />
            </div>

            {message && (
              <p
                className={
                  message.includes("success")
                    ? "text-sm text-green-600"
                    : "text-sm text-red-500"
                }
              >
                {message}
              </p>
            )}

            <div className="flex gap-2">
              {alreadySent ? (
                <p className="text-sm font-medium text-green-600">
                  ✓ This email has been sent
                </p>
              ) : (
                <Button
                  onClick={handleSend}
                  disabled={sending || !draft.professor_email}
                >
                  {sending ? "Sending..." : "Send Email"}
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => router.push("/matches")}
              >
                Back to Matches
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}