import { Source_Serif_4, Inter, IBM_Plex_Mono } from "next/font/google";

const serif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-serif",
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
        serif.variable +
        " " +
        sans.variable +
        " " +
        mono.variable +
        " min-h-screen bg-[#F5F6F3] text-[#10192B] font-sans"
      }
    >
      {/* NAV */}
      <header className="border-b border-[#D8DCE3]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="font-mono text-sm tracking-wide text-[#10192B]">
            <span className="text-[#3452E1]">[</span>ProfMatch
            <span className="text-[#3452E1]">]</span>
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <a href="/login" className="hover:text-[#3452E1]">
              Log in
            </a>
            <a
              href="/signup"
              className="rounded-md bg-[#10192B] px-4 py-2 text-[#F5F6F3] hover:bg-[#3452E1]"
            >
              Sign up
            </a>
          </nav>
        </div>
      </header>

      {/* HERO */}
      <section className="mx-auto max-w-6xl px-6 pb-24 pt-20">
        <div className="grid items-center gap-16 lg:grid-cols-2">
          <div>
            <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-[#3452E1]">
              For CSE grad school applicants
            </p>
            <h1
              className="mb-6 font-serif text-5xl font-semibold leading-[1.08] tracking-tight lg:text-6xl"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              Find the professor
              <br />
              your research
              <br />
              already agrees with.
            </h1>
            <p className="mb-8 max-w-md text-lg leading-relaxed text-[#3F4A5C]">
              ProfMatch reads your interests and papers, matches you to
              professors whose work actually overlaps with yours, and
              drafts the outreach email for you.
            </p>
            <div className="flex items-center gap-4">
              <a
                href="/signup"
                className="rounded-md bg-[#3452E1] px-6 py-3 text-sm font-medium text-white hover:bg-[#2941b8]"
              >
                Build your profile
              </a>
              <a
                href="#how-it-works"
                className="text-sm font-medium text-[#10192B] underline decoration-[#D8DCE3] underline-offset-4 hover:decoration-[#3452E1]"
              >
                See how it works
              </a>
            </div>
          </div>

          {/* SIGNATURE: live match preview */}
          <div className="relative rounded-2xl border border-[#D8DCE3] bg-white p-8 shadow-[0_1px_0_#D8DCE3]">
            <div className="mb-8 rounded-lg border border-[#D8DCE3] p-4">
              <p className="font-mono text-[11px] uppercase tracking-wide text-[#8A93A3]">
                Student profile
              </p>
              <p className="mt-1 font-serif text-lg" style={{ fontFamily: "var(--font-serif)" }}>
                Priya · MS Computer Science
              </p>
              <p className="mt-1 text-sm text-[#3F4A5C]">
                Reinforcement learning, dialogue systems
              </p>
            </div>

            <div className="relative my-2 flex items-center justify-center">
              <div className="h-10 w-px border-l border-dashed border-[#3452E1]" />
              <span className="absolute rounded-full bg-[#E8A94A] px-3 py-1 font-mono text-xs font-medium text-[#10192B]">
                97% match
              </span>
            </div>
            <div className="mt-8 rounded-lg border border-[#3452E1]/30 bg-[#3452E1]/[0.04] p-4">
              <p className="font-mono text-[11px] uppercase tracking-wide text-[#3452E1]">
                Matched professor
              </p>
              <p className="mt-1 font-serif text-lg" style={{ fontFamily: "var(--font-serif)" }}>
                Prof. Elena Ruiz · Stanford
              </p>
              <p className="mt-1 text-sm text-[#3F4A5C]">
                NLP &amp; dialogue systems lab
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section
        id="how-it-works"
        className="border-y border-[#D8DCE3] bg-white px-6 py-20"
      >
        <div className="mx-auto max-w-6xl">
          <h2
            className="mb-12 font-serif text-3xl font-semibold"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            How it works
          </h2>
          <div className="grid gap-10 md:grid-cols-3">
            {[
              {
                n: "01",
                title: "Build your profile",
                body:
                  "Add your university, GPA, GRE/IELTS scores, research interests, and paper links.",
              },
              {
                n: "02",
                title: "Get matched",
                body:
                  "We read your papers and interests, then rank professors by real research overlap.",
              },
              {
                n: "03",
                title: "Send outreach",
                body:
                  "Review an AI-drafted email written for each professor's work, then send it.",
              },
            ].map((step) => (
              <div key={step.n}>
                <p className="mb-3 font-mono text-sm text-[#3452E1]">
                  {step.n}
                </p>
                <h3 className="mb-2 text-lg font-semibold">{step.title}</h3>
                <p className="text-sm leading-relaxed text-[#3F4A5C]">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="px-6 py-20">
        <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-3">
          <div>
            <p className="mb-3 font-mono text-xs text-[#8A93A3]">
              cos(θ) matching
            </p>
            <h3 className="mb-2 text-lg font-semibold">
              Semantic, not keyword
            </h3>
            <p className="text-sm leading-relaxed text-[#3F4A5C]">
              Matching runs on meaning, not exact words — so "language
              agents" still finds a lab that only says "conversational AI."
            </p>
          </div>
          <div>
            <p className="mb-3 font-mono text-xs text-[#8A93A3]">
              Written per professor
            </p>
            <h3 className="mb-2 text-lg font-semibold">AI-drafted outreach</h3>
            <p className="text-sm leading-relaxed text-[#3F4A5C]">
              Every email references the professor&apos;s actual research —
              not a template with their name swapped in.
            </p>
          </div>
          <div>
            <p className="mb-3 font-mono text-xs text-[#8A93A3]">
              Ready to send
            </p>
            <h3 className="mb-2 text-lg font-semibold">
              Straight to their inbox
            </h3>
            <p className="text-sm leading-relaxed text-[#3F4A5C]">
              Review the draft, edit if you like, and send — no separate
              email client required.
            </p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#D8DCE3] px-6 py-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between font-mono text-xs text-[#8A93A3]">
          <span>ProfMatch</span>
          <span>Built for CSE grad school applicants</span>
        </div>
      </footer>
    </div>
  );
}