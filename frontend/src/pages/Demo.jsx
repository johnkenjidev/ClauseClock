// /demo — public, read-only synthetic ClauseClock V2 three-beat workspace.
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { DEMO } from "@/constants/testIds";

export default function Demo() {
  const navigate = useNavigate();

  useEffect(() => {
    // Hide standard AppShell layout header and footer dynamically
    const header = document.querySelector("header");
    const footer = document.querySelector("footer");
    if (header) header.style.display = "none";
    if (footer) footer.style.display = "none";

    document.body.setAttribute("data-theme", "dark");

    // Mockup IntersectionObserver lamp-reveal script
    var panels = document.querySelectorAll(".paper");
    if (!("IntersectionObserver" in window) ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches){
      panels.forEach(function(p){ p.classList.add("lit"); });
    } else {
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if (e.isIntersecting){ e.target.classList.add("lit"); io.unobserve(e.target); }
        });
      }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
      panels.forEach(function(p){ io.observe(p); });
    }

    return () => {
      if (header) header.style.display = "";
      if (footer) footer.style.display = "";
      document.body.removeAttribute("data-theme");
    };
  }, []);

  return (
    <div data-testid={DEMO.root} className="demo-wrapper-v3 min-h-screen">
      <style dangerouslySetInnerHTML={{ __html: `
        @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@400;500&family=IBM+Plex+Sans:wght@400;450;500;600&display=swap");

        /* Override standard AppShell container to match mockup full bleed */
        header { display: none !important; }
        footer { display: none !important; }
        main.flex-1 > div.mx-auto.max-w-6xl.px-6.py-14 {
          max-width: 100% !important;
          padding: 0 !important;
        }

        :root {
          /* ground */
          --ground:        #070A09;   /* near-black, green cast */
          --ground-2:      #0C110F;   /* closing band only */
          --ground-display:#BCC6C0;   /* hero only — sits just under paper luminance */
          --ground-text:   #A9B5AE;   /* deliberately below paper luminance */
          --ground-muted:  #6F7E77;
          --ground-rule:   rgba(221,228,223,0.11);

          /* paper — evidence surface */
          --paper:         #CFC9BC;
          --paper-edge:    #B8B09F;
          --ink:           #1A1813;
          --ink-muted:     #565045;
          --ink-rule:      rgba(26,24,19,0.20);
          --ink-hairline:  rgba(26,24,19,0.48);

          /* scale */
          --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px;
          --s6:32px; --s7:48px; --s8:64px; --s9:96px; --s10:128px;
          --radius: 2px;
          --measure: 34rem;
          --panel-max: 54rem;
        }

        .demo-wrapper-v3 {
          background: var(--ground);
          color: var(--ground-text);
          font-family: "IBM Plex Sans", system-ui, sans-serif;
          font-size: 16px;
          line-height: 1.6;
          -webkit-font-smoothing: antialiased;
          min-height: 100vh;
        }

        .demo-wrapper-v3 .masthead {
          border-bottom: 1px solid var(--ground-rule);
          padding: var(--s5) 0;
        }
        .demo-wrapper-v3 .masthead .wrap { display: flex; align-items: baseline; justify-content: space-between; gap: var(--s4); }
        .demo-wrapper-v3 .mark {
          font-family: "IBM Plex Sans Condensed", sans-serif;
          font-weight: 500; font-size: 1.0625rem; letter-spacing: 0.01em;
          color: var(--ground-text); text-decoration: none;
        }
        .demo-wrapper-v3 .mark span { color: var(--ground-muted); }
        .demo-wrapper-v3 .masthead a.quiet {
          font-size: 0.875rem; color: var(--ground-muted); text-decoration: none;
        }
        .demo-wrapper-v3 .masthead a.quiet:hover { color: var(--ground-text); }

        .demo-wrapper-v3 .hero { padding: var(--s9) 0 var(--s8); }
        .demo-wrapper-v3 .hero h1 {
          font-family: "IBM Plex Sans Condensed", sans-serif;
          font-weight: 400;
          color: var(--ground-display);
          font-size: clamp(2.375rem, 6.4vw, 4.375rem);
          line-height: 1.02;
          letter-spacing: -0.025em;
          margin: 0 0 var(--s5);
          max-width: 19ch;
        }
        .demo-wrapper-v3 .hero p {
          margin: 0; color: var(--ground-muted); font-size: 1rem; max-width: var(--measure);
        }

        .demo-wrapper-v3 .beat-intro { padding: var(--s8) 0 var(--s6); }
        .demo-wrapper-v3 .eyebrow {
          font-size: 0.6875rem; font-weight: 500; text-transform: uppercase;
          letter-spacing: 0.14em; color: var(--ground-muted);
          margin: 0 0 var(--s3);
        }
        .demo-wrapper-v3 .beat-intro h2 {
          font-family: "IBM Plex Sans Condensed", sans-serif;
          font-weight: 400; font-size: clamp(1.375rem, 3vw, 1.75rem);
          line-height: 1.25; margin: 0 0 var(--s3); max-width: 26ch;
          color: var(--ground-display);
        }
        .demo-wrapper-v3 .beat-intro p { margin: 0; color: var(--ground-muted); max-width: var(--measure); }

        .demo-wrapper-v3 .paper {
          position: relative;
          max-width: var(--panel-max);
          margin: 0 auto var(--s5);
          background-color: var(--paper);
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23g)' opacity='0.07'/%3E%3C/svg%3E");
          background-blend-mode: multiply;
          color: var(--ink);
          border-radius: var(--radius);
          border-top: 1px solid #DBD5C7;
          box-shadow: 0 32px 64px -28px rgba(0,0,0,0.75),
                     0 2px 6px rgba(0,0,0,0.35);
          padding: var(--s7) var(--s7) var(--s6);
        }
        .demo-wrapper-v3 .paper::before {
          content: ""; position: absolute; inset: -14% -6% -8%;
          background: radial-gradient(58% 50% at 50% 34%, rgba(207,201,188,0.03), transparent 72%);
          pointer-events: none; z-index: -1;
        }

        .demo-wrapper-v3 .provenance {
          font-size: 0.75rem; color: var(--ink-muted);
          padding-bottom: var(--s4); margin-bottom: var(--s5);
          border-bottom: 1px solid var(--ink-rule);
        }

        .demo-wrapper-v3 .clause {
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.8125rem; line-height: 1.85;
          margin: 0 0 var(--s6);
          color: var(--ink);
          border-left: 2px solid var(--ink-hairline);
          padding-left: var(--s5);
        }

        .demo-wrapper-v3 .ledger { margin: 0; }
        .demo-wrapper-v3 .row {
          display: flex; align-items: baseline; justify-content: space-between;
          gap: var(--s5); padding: var(--s3) 0;
        }
        .demo-wrapper-v3 .row dt { color: var(--ink-muted); font-size: 0.9375rem; margin: 0; }
        .demo-wrapper-v3 .row dd {
          margin: 0; font-size: 0.9375rem; color: var(--ink); text-align: right;
          font-variant-numeric: lining-nums tabular-nums;
        }
        .demo-wrapper-v3 .row.result {
          border-top: 1px solid var(--ink-hairline);
          margin-top: var(--s3); padding-top: var(--s5);
        }
        .demo-wrapper-v3 .row.result dt { color: var(--ink); }
        .demo-wrapper-v3 .row.absent dd { color: var(--ink-muted); }

        .demo-wrapper-v3 .derivation {
          margin: var(--s6) 0 0; font-size: 0.8125rem; color: var(--ink-muted);
          padding-top: var(--s4); border-top: 1px solid var(--ink-rule);
        }

        .demo-wrapper-v3 .reason {
          margin: var(--s6) 0 0; font-size: 0.9375rem; line-height: 1.65;
          color: var(--ink); max-width: 46ch;
        }
        .demo-wrapper-v3 .reason + .reason { margin-top: var(--s3); color: var(--ink-muted); }

        .demo-wrapper-v3 .record { margin: 0; }
        .demo-wrapper-v3 .entry {
          display: grid; grid-template-columns: 8.5rem 1fr;
          gap: var(--s5); padding: var(--s4) 0;
          border-bottom: 1px solid var(--ink-rule);
        }
        .demo-wrapper-v3 .entry:last-of-type { border-bottom: 0; }
        .demo-wrapper-v3 .entry .when {
          font-size: 0.8125rem; color: var(--ink-muted);
          font-variant-numeric: lining-nums tabular-nums;
        }
        .demo-wrapper-v3 .entry .what { font-size: 0.9375rem; color: var(--ink); }
        .demo-wrapper-v3 .entry .what small {
          display: block; font-size: 0.8125rem; color: var(--ink-muted); margin-top: 2px;
        }

        .demo-wrapper-v3 .receipt {
          margin-top: var(--s6); padding-top: var(--s6);
          border-top: 1px dashed var(--ink-hairline);
        }
        .demo-wrapper-v3 .receipt .label {
          font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.12em;
          color: var(--ink-muted); margin: 0 0 var(--s3);
        }
        .demo-wrapper-v3 .hash {
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.8125rem; line-height: 1.7; letter-spacing: 0.02em;
          margin: 0; color: var(--ink); word-break: break-all;
        }
        .demo-wrapper-v3 .receipt .note {
          margin: var(--s4) 0 0; font-size: 0.8125rem; color: var(--ink-muted); max-width: 44ch;
        }

        .demo-wrapper-v3 .close {
          background: var(--ground-2);
          border-top: 1px solid var(--ground-rule);
          margin-top: var(--s9); padding: var(--s9) 0;
        }
        .demo-wrapper-v3 .close h2 {
          font-family: "IBM Plex Sans Condensed", sans-serif;
          font-weight: 400; font-size: clamp(1.5rem, 3.4vw, 2rem);
          line-height: 1.2; margin: 0 0 var(--s4); max-width: 22ch;
          color: var(--ground-display);
        }
        .demo-wrapper-v3 .close p { margin: 0 0 var(--s6); color: var(--ground-muted); max-width: var(--measure); }
        .demo-wrapper-v3 .cta {
          display: inline-block; background: var(--paper); color: var(--ink);
          font-family: "IBM Plex Sans", sans-serif; font-size: 1rem; font-weight: 500;
          text-decoration: none; padding: var(--s4) var(--s6); border-radius: var(--radius);
          border: 1px solid var(--paper-edge);
          border-top-color: #DBD5C7;
          box-shadow: 0 12px 28px -12px rgba(0,0,0,0.85), 0 1px 2px rgba(0,0,0,0.4);
          transition: transform 120ms ease, box-shadow 120ms ease;
          cursor: pointer;
        }
        .demo-wrapper-v3 .cta:hover { transform: translateY(-2px); box-shadow: 0 18px 36px -12px rgba(0,0,0,0.9), 0 1px 2px rgba(0,0,0,0.4); }
        .demo-wrapper-v3 .cta:focus-visible { outline: 2px solid var(--paper); outline-offset: 3px; }
        .demo-wrapper-v3 .close .fineprint {
          margin: var(--s5) 0 0; font-size: 0.8125rem; color: var(--ground-muted);
        }

        .demo-wrapper-v3 footer { padding: var(--s6) 0; border-top: 1px solid var(--ground-rule); }
        .demo-wrapper-v3 footer .wrap { display: flex; justify-content: space-between; gap: var(--s4); flex-wrap: wrap; }
        .demo-wrapper-v3 footer p { margin: 0; font-size: 0.8125rem; color: var(--ground-muted); }

        /* lamp reveal */
        .demo-wrapper-v3 .paper { opacity: 0; transform: translateY(10px); transition: opacity 520ms ease, transform 520ms ease; }
        .demo-wrapper-v3 .paper.lit { opacity: 1; transform: none; }

        @media (prefers-reduced-motion: reduce) {
          .demo-wrapper-v3 .paper { opacity: 1; transform: none; transition: none; }
          .demo-wrapper-v3 .cta { transition: none; }
        }

        @media (max-width: 640px) {
          .demo-wrapper-v3 .wrap { padding: 0 var(--s4); }
          .demo-wrapper-v3 .hero { padding: var(--s7) 0 var(--s6); }
          .demo-wrapper-v3 .beat-intro { padding: var(--s7) 0 var(--s5); }
          .demo-wrapper-v3 .paper {
            margin-left: 0; margin-right: 0; border-radius: 0;
            padding: var(--s6) var(--s4) var(--s5);
            box-shadow: 0 18px 40px -22px rgba(0,0,0,0.8);
          }
          .demo-wrapper-v3 .clause { padding-left: var(--s4); font-size: 0.78125rem; }
          .demo-wrapper-v3 .entry { grid-template-columns: 1fr; gap: var(--s1); }
          .demo-wrapper-v3 .entry .when { order: -1; }
          .demo-wrapper-v3 .close { padding: var(--s7) 0; }
        }

        @media (max-width: 480px) {
          .demo-wrapper-v3 .row { display: block; padding: var(--s3) 0; }
          .demo-wrapper-v3 .row dt { font-size: 0.8125rem; }
          .demo-wrapper-v3 .row dd { text-align: left; margin-top: 2px; font-size: 1rem; }
          .demo-wrapper-v3 .row.result { padding-top: var(--s4); }
        }
      ` }} />

      <header className="masthead">
        <div className="wrap">
          <a className="mark" href="#" onClick={(e) => { e.preventDefault(); navigate("/demo"); }}>
            ClauseClock<span>&nbsp;/ demo</span>
          </a>
          <a className="quiet" href="#" onClick={(e) => { e.preventDefault(); navigate("/login"); }}>
            Sign in
          </a>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="wrap">
            <h1>Every deadline, traced to the sentence it came from.</h1>
            <p>ClauseClock reads your vendor agreements, computes the dates the contract actually supports, and shows its work. Three real outputs below — including one where it declines to answer. <strong>All demo workspace data is synthetic.</strong></p>
          </div>
        </section>

        {/* ===================== BEAT 1 — THE FINDING ===================== */}
        <section className="beat-intro">
          <div className="wrap">
            <p className="eyebrow">A finding</p>
            <h2>A deadline, and the sentence it came from.</h2>
            <p>Every date on this card is derived from the quoted text. Nothing is summarized or restated.</p>
          </div>
        </section>

        <article className="paper">
          <p className="provenance">Vendor Services Agreement — Meridian Supply Co. &nbsp;·&nbsp; § 4.1 Term and Renewal &nbsp;·&nbsp; page 3</p>

          <p className="clause">&ldquo;This Agreement shall commence on December 1, 2025 (the &ldquo;Effective Date&rdquo;) and shall continue for an initial term of three (3) years. This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal not less than sixty (60) days prior to the end of the then-current term.&rdquo;</p>

          <dl className="ledger">
            <div className="row"><dt>Effective date</dt><dd>December 1, 2025</dd></div>
            <div className="row"><dt>Initial term</dt><dd>3 years</dd></div>
            <div className="row"><dt>Term ends</dt><dd>November 30, 2028</dd></div>
            <div className="row"><dt>Renews</dt><dd>December 1, 2028</dd></div>
            <div className="row"><dt>Notice required</dt><dd>60 days before term end</dd></div>
            <div className="row result"><dt>Notice deadline</dt><dd>October 1, 2028</dd></div>
          </dl>

          <p className="derivation">Computed from the quoted text, not inferred. ClauseClock asks you to confirm a finding before it starts tracking the date.</p>
        </article>

        {/* ===================== BEAT 2 — THE REFUSAL ===================== */}
        <section className="beat-intro">
          <div className="wrap">
            <p className="eyebrow">A refusal</p>
            <h2>When the contract {"doesn't"} say, ClauseClock {"doesn't"} guess.</h2>
            <p>Same document type, same clause structure, one missing input.</p>
          </div>
        </section>

        <article className="paper">
          <p className="provenance">Master Services Agreement — draft, unexecuted &nbsp;·&nbsp; § 2.1 Term &nbsp;·&nbsp; page 1</p>

          <p className="clause">&ldquo;This Agreement is effective as of [Signing Date] and shall remain in force for an initial period of twenty-four (24) months, renewing automatically thereafter unless terminated in accordance with Section 9.&rdquo;</p>

          <dl className="ledger">
            <div className="row absent"><dt>Effective date</dt><dd>Not stated in the document</dd></div>
            <div className="row"><dt>Initial term</dt><dd>24 months</dd></div>
            <div className="row"><dt>Renewal</dt><dd>Automatic</dd></div>
            <div className="row result absent"><dt>Notice deadline</dt><dd>Cannot compute from this document</dd></div>
          </dl>

          <p className="reason">The effective date is an unfilled placeholder. Without it, the renewal date and the notice deadline cannot be derived from this document.</p>
          <p className="reason">Add the signing date and ClauseClock will compute both. Until then, this contract stays in your portfolio without a tracked deadline.</p>
        </article>

        {/* ===================== BEAT 3 — THE RECORD ===================== */}
        <section className="beat-intro">
          <div className="wrap">
            <p className="eyebrow">A record</p>
            <h2>From finding to confirmed outcome.</h2>
            <p>Detection is the first step. ClauseClock keeps the evidence that the deadline was met.</p>
          </div>
        </section>

        <article className="paper">
          <p className="provenance">Meridian Supply Co. &nbsp;·&nbsp; Non-renewal, initial term</p>

          <dl className="record">
            <div className="entry">
              <div className="when">Mar 14, 2026</div>
              <div className="what">Finding confirmed<small>Notice deadline — October 1, 2028</small></div>
            </div>
            <div className="entry">
              <div className="when">Sep 4, 2028</div>
              <div className="what">Non-renewal notice sent<small>Email to contracts@meridiansupply.com</small></div>
            </div>
            <div className="entry">
              <div className="when">Sep 4, 2028</div>
              <div className="what">Evidence attached<small>notice-meridian-2028-09-04.pdf — 214 KB</small></div>
            </div>
            <div className="entry">
              <div className="when">Sep 11, 2028</div>
              <div className="what">Outcome confirmed by vendor<small>20 days before the deadline</small></div>
            </div>
          </dl>

          <div className="receipt">
            <p className="label">Evidence fingerprint · SHA-256</p>
            <p className="hash">9f2c41ab7e58d0c3b6a94f17e2d85c0a3b71f6e94d2c8a05b3e7f19c4a6d82b0</p>
            <p className="note">Recorded when the file was attached. Any change to the file changes this value.</p>
          </div>
        </article>

        {/* ===================== CLOSE ===================== */}
        <section className="close">
          <div className="wrap">
            <h2>Start with one contract.</h2>
            <p>Upload a vendor agreement and see what ClauseClock finds — and what it {"won't"} claim to know.</p>
            <button className="cta" onClick={() => navigate("/signup")}>Upload a contract</button>
            <p className="fineprint">No card required. ClauseClock is not a law firm and does not provide legal advice.</p>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap">
          <p>ClauseClock</p>
          <p>Synthetic Demo Workspace — V2 demo composition</p>
        </div>
      </footer>
    </div>
  );
}
