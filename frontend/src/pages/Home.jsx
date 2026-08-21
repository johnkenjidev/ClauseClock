// / — public ClauseClock homepage. Reuses the existing dark design system.
// No pricing, testimonials, feature grid, or help center.
import { Link } from "react-router-dom";
import { Clock8 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Eyebrow } from "@/components/cc/Primitives";

export default function Home() {
  return (
    <div data-testid="home-page" className="min-h-screen bg-paper">
      <header className="border-b border-rule">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock8 className="h-5 w-5 text-seal" strokeWidth={2.25} />
            <span className="font-archivo-expanded font-bold tracking-tight text-[18px] uppercase text-ink">
              ClauseClock
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/demo" data-testid="home-demo-link"
              className="cc-days-remaining text-ink-soft hover:text-ink">
              See it working →
            </Link>
            <Link to="/login" data-testid="home-signin-link">
              <Button variant="outline" className="rounded-full h-9 px-4 border-rule text-ink hover:bg-card">
                Sign in
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-24">
        <Eyebrow>Contract deadlines &amp; obligations</Eyebrow>
        <div className="cc-seal-rule mt-4 mb-6" />
        <h1 className="font-archivo font-semibold text-ink text-4xl sm:text-5xl leading-[1.08] tracking-tight">
          Know what matters<br className="hidden sm:block" /> before the deadline does.
        </h1>
        <p className="cc-plain-english text-ink-soft mt-6 max-w-xl">
          ClauseClock finds renewal, pricing, termination, claim, dispute, and notice obligations,
          verifies every finding against the contract language, and turns confirmed deadlines into a clear action queue.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <Link to="/signup" data-testid="home-get-started">
            <Button className="bg-ink text-paper hover:bg-ink/90 rounded-full h-11 px-6">
              Get started
            </Button>
          </Link>
          <Link to="/demo" data-testid="home-sample">
            <Button variant="ghost" className="rounded-full h-11 px-4 text-ink-soft hover:text-ink hover:bg-card">
              See a sample workspace →
            </Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
