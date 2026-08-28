import Link from "next/link";
import { Space_Grotesk, Inter, IBM_Plex_Mono } from "next/font/google";

const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});
const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export default function Home() {
  return (
    <div
      className={
        display.variable +
        " " +
        sans.variable +
        " " +
        mono.variable +
        " min-h-screen bg-[#06070A] font-sans text-[#F5F6F8]"
      }
    >
      {/* NAV */}
      <header className="fixed top-0 z-50 w-full border-b border-[#1C2029]/60 bg-[#06070A]/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div
            className="text-sm font-semibold tracking-wide"
            style={{ fontFamily: "var(--font-display)" }}
          >
            PROFMATCH
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/login" className="text-[#9AA3B2] hover:text-[#F5F6F8]">
              Log in
            </Link>
            <Link
              href="/signup"
              className="rounded-full bg-[#4DA8FF] px-5 py-2 text-sm font-medium text-[#06070A] transition hover:bg-[#6DB8FF]"
            >
              Get Matched
            </Link>
          </nav>
        </div>
      </header>

      {/* HERO */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-20">
        {/* ambient glow */}
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#4DA8FF]/10 blur-[120px]" />

        <p
          className="relative mb-6 font-mono text-xs uppercase tracking-[0.3em] text-[#4DA8FF]"
        >
          Live faculty network — United States
        </p>

        <h1
          className="relative mb-6 max-w-4xl text-center text-6xl font-semibold leading-[1.05] tracking-tight lg:text-7xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Connect to the
          <br />
          professor already
          <br />
          working on your idea.
        </h1>

        <p className="relative mb-10 max-w-lg text-center text-lg text-[#9AA3B2]">
          ProfMatch scans faculty research across US universities and finds
          the strongest signal — then writes the email for you.
        </p>

        <div className="relative flex items-center gap-4">
          <Link
            href="/signup"
            className="rounded-full bg-[#4DA8FF] px-8 py-3.5 text-sm font-semibold text-[#06070A] transition hover:bg-[#6DB8FF]"
          >
            Build your profile
          </Link>
          <Link
            href="#network"
            className="rounded-full border border-[#1C2029] px-8 py-3.5 text-sm font-medium text-[#F5F6F8] transition hover:border-[#4DA8FF]/50"
          >
            See how it works
          </Link>
        </div>

        {/* SIGNATURE: signal/network readout */}
        <div className="relative mt-20 w-full max-w-2xl rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-8">
          <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-wide text-[#9AA3B2]">
            <span>Node · You</span>
            <span>Signal strength</span>
            <span>Node · Faculty</span>
          </div>

          <div className="my-6 flex items-center gap-4">
            <div className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#F5F6F8]" />
            <div className="relative h-px flex-1 bg-gradient-to-r from-[#F5F6F8] via-[#4DA8FF] to-[#4DA8FF]">
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#4DA8FF] px-3 py-1 font-mono text-xs font-semibold text-[#06070A]">
                97%
              </span>
            </div>
            <div className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#4DA8FF] shadow-[0_0_12px_2px_rgba(77,168,255,0.6)]" />
          </div>

          <div className="flex items-center justify-between text-sm">
            <div>
              <p className="font-medium">Priya M.</p>
              <p className="text-[#9AA3B2]">Reinforcement learning</p>
            </div>
            <div className="text-right">
              <p className="font-medium">Prof. Elena Ruiz</p>
              <p className="text-[#9AA3B2]">Stanford · NLP lab</p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="network" className="border-t border-[#1C2029] px-6 py-28">
        <div className="mx-auto max-w-6xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-[0.3em] text-[#4DA8FF]">
            How the network finds a match
          </p>
          <h2
            className="mb-16 max-w-xl text-4xl font-semibold leading-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Three signals, one connection.
          </h2>

          <div className="grid gap-12 md:grid-cols-3">
            {[
              {
                n: "01",
                title: "Broadcast your interests",
                body: "University, GPA, GRE/IELTS, research interests, papers — your full research identity.",
              },
              {
                n: "02",
                title: "Scan the faculty network",
                body: "We read live research data across US universities and rank by real overlap, not keywords.",
              },
              {
                n: "03",
                title: "Send the strongest signal",
                body: "Review an email written for that professor's actual work, then send it straight to their inbox.",
              },
            ].map((step) => (
              <div key={step.n}>
                <p className="mb-4 font-mono text-sm text-[#4DA8FF]">{step.n}</p>
                <h3 className="mb-2 text-lg font-semibold">{step.title}</h3>
                <p className="text-sm leading-relaxed text-[#9AA3B2]">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="border-t border-[#1C2029] px-6 py-28">
        <div className="mx-auto grid max-w-6xl gap-6 md:grid-cols-3">
          {[
            {
              title: "Semantic, not keyword",
              body: "Matching runs on meaning — \"language agents\" still finds a lab that only says \"conversational AI.\"",
            },
            {
              title: "Written per professor",
              body: "Every draft references their actual research, never a template with the name swapped.",
            },
            {
              title: "Direct to their inbox",
              body: "Review the draft, edit if you like, send — no separate email client required.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-[#1C2029] bg-[#0B0D12] p-6 transition hover:border-[#4DA8FF]/40"
            >
              <h3 className="mb-2 font-semibold">{f.title}</h3>
              <p className="text-sm leading-relaxed text-[#9AA3B2]">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[#1C2029] px-6 py-28 text-center">
        <h2
          className="mx-auto mb-8 max-w-xl text-4xl font-semibold leading-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Your research already has an audience.
        </h2>
        <Link
          href="/signup"
          className="inline-block rounded-full bg-[#4DA8FF] px-10 py-4 text-sm font-semibold text-[#06070A] transition hover:bg-[#6DB8FF]"
        >
          Find your match
        </Link>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#1C2029] px-6 py-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between font-mono text-xs text-[#9AA3B2]">
          <span>PROFMATCH</span>
          <span>Built for US CSE grad school applicants</span>
        </div>
      </footer>
    </div>
  );
}