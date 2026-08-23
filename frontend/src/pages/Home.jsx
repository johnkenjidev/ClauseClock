// / — public ClauseClock homepage. Reuses the existing dark design system.
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  useEffect(() => {
    var panels = document.querySelectorAll('.paper');
    if (!('IntersectionObserver' in window) ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches){
      panels.forEach(function(p){ p.classList.add('lit'); });
      return;
    }
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){ e.target.classList.add('lit'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    panels.forEach(function(p){ io.observe(p); });
  }, []);

  return (
    <div data-testid="home-page" className="homepage-wrapper min-h-screen">
      <style dangerouslySetInnerHTML={{ __html: `
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@400;500&family=IBM+Plex+Sans:wght@400;450;500;600&display=swap');

        .homepage-wrapper {
          background: #070A09;
          color: #A9B5AE;
          font-family: "IBM Plex Sans", system-ui, sans-serif;
          font-size: 16px;
          line-height: 1.6;
          -webkit-font-smoothing: antialiased;
          overflow-x: hidden;
          min-height: 100vh;
        }

        .homepage-wrapper :root {
          --ground:        #070A09;
          --ground-2:      #0C110F;
          --ground-display:#BCC6C0;
          --ground-text:   #A9B5AE;
          --ground-muted:  #6F7E77;
          --ground-rule:   rgba(221,228,223,0.11);

          --paper:         #CFC9BC;
          --paper-edge:    #B8B09F;
          --ink:           #1A1813;
          --ink-muted:     #565045;
          --ink-rule:      rgba(26,24,19,0.20);
          --ink-hairline:  rgba(26,24,19,0.48);

          --stamp:         #A93226;

          --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px;
          --s6:32px; --s7:48px; --s8:64px; --s9:96px; --s10:128px;
          --radius: 2px;
          --measure: 34rem;
          --panel-max: 54rem;
        }

        .homepage-wrapper .mono{font-family:"IBM Plex Mono",monospace}
        .homepage-wrapper .eyebrow{
          font-size:0.6875rem;font-weight:500;text-transform:uppercase;
          letter-spacing:0.14em;color: #6F7E77;margin:0 0 12px;
        }
        .homepage-wrapper h2.sec{
          font-family:"IBM Plex Sans Condensed",sans-serif;
          font-weight:400;color:#BCC6C0;
          font-size:clamp(1.5rem,4vw,2.125rem);line-height:1.16;
          letter-spacing:-0.015em;margin:0 0 16px;max-width:24ch;
        }
        .homepage-wrapper .lede{margin:0;color:#6F7E77;max-width:34rem;}

        /* ---------- header ---------- */
        .homepage-wrapper .masthead{border-bottom:1px solid rgba(221,228,223,0.11);padding:16px 0;}
        .homepage-wrapper .masthead .wrap{display:flex;align-items:baseline;justify-content:space-between;gap:16px;}
        .homepage-wrapper .mark{
          font-family:"IBM Plex Sans Condensed",sans-serif;font-weight:500;
          font-size:1.0625rem;letter-spacing:0.01em;color:#BCC6C0;
          text-decoration:none;white-space:nowrap;
        }
        .homepage-wrapper .masthead a.quiet{font-size:0.875rem;color:#6F7E77;text-decoration:none;white-space:nowrap;}
        .homepage-wrapper .masthead a.quiet:hover{color:#A9B5AE;}

        /* ---------- 1. hero ---------- */
        .homepage-wrapper .hero{padding:64px 0 64px;}
        @media (min-width:641px){ .homepage-wrapper .hero{padding:128px 0 96px;} }
        .homepage-wrapper .hero h1{
          font-family:"IBM Plex Sans Condensed",sans-serif;font-weight:400;
          color:#BCC6C0;
          font-size:clamp(2.125rem,5.8vw,3.875rem);
          line-height:1.04;letter-spacing:-0.025em;
          margin:0 0 24px;max-width:21ch;
        }
        .homepage-wrapper .hero p{margin:0 0 48px;color:#6F7E77;max-width:34rem;}
        .homepage-wrapper .actions{display:flex;align-items:center;gap:24px;flex-wrap:wrap;}
        .homepage-wrapper .cta{
          display:inline-block;background:#CFC9BC;color:#1A1813;
          font-size:1rem;font-weight:500;text-decoration:none;
          padding:16px 32px;border-radius:2px;
          border:1px solid #B8B09F;border-top-color:#DBD5C7;
          box-shadow:0 12px 28px -12px rgba(0,0,0,0.85),0 1px 2px rgba(0,0,0,0.4);
          transition:transform 120ms ease,box-shadow 120ms ease;
          cursor:pointer;
        }
        .homepage-wrapper .cta:hover{transform:translateY(-2px);box-shadow:0 18px 36px -12px rgba(0,0,0,0.9),0 1px 2px rgba(0,0,0,0.4);}
        .homepage-wrapper .cta:focus-visible{outline:2px solid #CFC9BC;outline-offset:3px;}
        .homepage-wrapper .textlink{font-size:0.9375rem;color:#6F7E77;text-decoration:none;border-bottom:1px solid rgba(221,228,223,0.11);padding-bottom:2px;}
        .homepage-wrapper .textlink:hover{color:#A9B5AE;}

        /* ---------- 2. what it catches ---------- */
        .homepage-wrapper .catches{padding:64px 0;border-top:1px solid rgba(221,228,223,0.11);}
        .homepage-wrapper .types{
          list-style:none;margin:48px 0 0;padding:0;
          display:grid;grid-template-columns:1fr;
          column-gap:48px;row-gap:24px;
        }
        @media (min-width:721px){ .homepage-wrapper .types{grid-template-columns:1fr 1fr;} }
        .homepage-wrapper .types li{min-width:0;}
        .homepage-wrapper .types .t{display:block;color:#A9B5AE;font-size:1rem;}
        .homepage-wrapper .types .d{display:block;color:#6F7E77;font-size:0.875rem;margin-top:8px;}

        /* ---------- 3. evidence ---------- */
        .homepage-wrapper .evidence-intro{padding:64px 0 32px;border-top:1px solid rgba(221,228,223,0.11);}

        .homepage-wrapper .paper{
          position:relative;max-width:54rem;margin:0 auto;
          background-color:#CFC9BC;
          background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23g)' opacity='0.07'/%3E%3C/svg%3E");
          background-blend-mode:multiply;
          color:#1A1813;border-radius:0;border-top:1px solid #DBD5C7;
          box-shadow:0 18px 40px -22px rgba(0,0,0,0.8);
          padding:32px 16px 24px;
        }
        @media (min-width:641px){
          .homepage-wrapper .paper{
            border-radius:2px;padding:48px 48px 32px;
            box-shadow:0 32px 64px -28px rgba(0,0,0,0.75),0 2px 6px rgba(0,0,0,0.35);
          }
        }
        .homepage-wrapper .paper::before{
          content:"";position:absolute;inset:-14% -6% -8%;
          background:radial-gradient(58% 50% at 50% 34%,rgba(207,201,188,0.03),transparent 72%);
          pointer-events:none;z-index:-1;
        }
        .homepage-wrapper .provenance{
          font-size:0.75rem;color:#565045;
          padding-bottom:16px;margin-bottom:24px;
          border-bottom:1px solid rgba(26,24,19,0.20);
        }
        .homepage-wrapper .clause{
          font-family:"IBM Plex Mono",monospace;
          font-size:0.78125rem;line-height:1.85;margin:0 0 32px;
          color:#1A1813;border-left:2px solid rgba(26,24,19,0.48);padding-left:16px;
        }
        @media (min-width:641px){ .homepage-wrapper .clause{font-size:0.8125rem;padding-left:24px;} }

        .homepage-wrapper .ledger{margin:0;}
        .homepage-wrapper .row{display:flex;align-items:baseline;justify-content:space-between;gap:24px;padding:12px 0;}
        .homepage-wrapper .row dt{color:#565045;font-size:0.9375rem;margin:0;min-width:0;}
        .homepage-wrapper .row dd{margin:0;font-size:0.9375rem;color:#1A1813;text-align:right;min-width:0;
                font-variant-numeric:lining-nums tabular-nums;}
        .homepage-wrapper .row.result{border-top:1px solid rgba(26,24,19,0.48);margin-top:12px;padding-top:24px;}
        .homepage-wrapper .row.result dt{color:#1A1813;}
        .homepage-wrapper .row-note{padding:0 0 12px;}
        .homepage-wrapper .row-note p{
          font-family:"IBM Plex Mono",monospace;
          font-size:0.75rem;line-height:1.7;color:#565045;
          margin:0;padding-left:16px;border-left:1px solid rgba(26,24,19,0.20);
        }
        .homepage-wrapper .derivation{
          margin:32px 0 0;font-size:0.8125rem;color:#565045;
          padding-top:16px;border-top:1px solid rgba(26,24,19,0.20);
        }

        /* ---------- 4. how it works ---------- */
        .homepage-wrapper .how{padding:64px 0;}
        .homepage-wrapper .steps{list-style:none;margin:48px 0 0;padding:0;counter-reset:step;}
        .homepage-wrapper .steps li{
          display:grid;grid-template-columns:2.25rem 1fr;gap:16px;
          padding:16px 0;border-bottom:1px solid rgba(221,228,223,0.11);
        }
        .homepage-wrapper .steps li:last-child{border-bottom:0;}
        .homepage-wrapper .steps li::before{
          counter-increment:step;content:counter(step,decimal-leading-zero);
          color:#6F7E77;font-size:0.8125rem;
          font-variant-numeric:lining-nums tabular-nums;padding-top:3px;
        }
        .homepage-wrapper .steps .t{display:block;color:#A9B5AE;}
        .homepage-wrapper .steps .d{display:block;color:#6F7E77;font-size:0.875rem;margin-top:2px;}

        /* ---------- 5. why the dates hold ---------- */
        .homepage-wrapper .integrity{padding:64px 0;border-top:1px solid rgba(221,228,223,0.11);}
        .homepage-wrapper .claims{list-style:none;margin:48px 0 0;padding:0;}
        .homepage-wrapper .claims li{padding:24px 0;border-bottom:1px solid rgba(221,228,223,0.11);max-width:34rem;}
        .homepage-wrapper .claims li:last-child{border-bottom:0;}
        .homepage-wrapper .claims .t{
          display:block;font-family:"IBM Plex Sans Condensed",sans-serif;
          font-size:1.1875rem;color:#BCC6C0;letter-spacing:-0.01em;
        }
        .homepage-wrapper .claims .d{display:block;color:#6F7E77;font-size:0.9375rem;margin-top:8px;}
        .homepage-wrapper .integrity .after{margin:32px 0 0;font-size:0.9375rem;color:#6F7E77;}

        /* ---------- 6. close ---------- */
        .homepage-wrapper .close{background:#0C110F;border-top:1px solid rgba(221,228,223,0.11);padding:64px 0;}
        @media (min-width:641px){ .homepage-wrapper .close{padding:96px 0;} }
        .homepage-wrapper .close h2{
          font-family:"IBM Plex Sans Condensed",sans-serif;font-weight:400;
          color:#BCC6C0;font-size:clamp(1.625rem,4.4vw,2.25rem);
          line-height:1.14;letter-spacing:-0.02em;margin:0 0 16px;max-width:20ch;
        }
        .homepage-wrapper .close p{margin:0 0 32px;color:#6F7E77;max-width:34rem;}
        .homepage-wrapper .close .fineprint{margin:24px 0 0;font-size:0.8125rem;color:#6F7E77;}

        .homepage-wrapper footer{padding:32px 0;border-top:1px solid rgba(221,228,223,0.11);}
        .homepage-wrapper footer .wrap{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;}
        .homepage-wrapper footer p{margin:0;font-size:0.8125rem;color:#6F7E77;}

        /* ---------- paper animations ---------- */
        .homepage-wrapper .paper{opacity:0;transform:translateY(10px);transition:opacity 520ms ease,transform 520ms ease;}
        .homepage-wrapper .paper.lit{opacity:1;transform:none;}
        @media (prefers-reduced-motion:reduce){
          .homepage-wrapper .paper{opacity:1;transform:none;transition:none;}
          .homepage-wrapper .cta{transition:none;}
        }

        .homepage-wrapper .wrap{max-width:54rem;margin:0 auto;padding:0 16px;}
        @media (min-width:641px){ .homepage-wrapper .wrap{padding:0 24px;} }
      ` }} />

      <header className="masthead">
        <div className="wrap">
          <Link className="mark" to="/">ClauseClock</Link>
          <Link className="quiet" to="/login">Sign in</Link>
        </div>
      </header>

      <main>
        {/* ===================== 1. HERO ===================== */}
        <section className="hero">
          <div className="wrap">
            <h1>Everything your contracts require of you, and the exact words that require it.</h1>
            <p>ClauseClock reads your vendor agreements and finds the deadlines, rights and money buried in them. Every finding shows the clause it came from. When a contract {"doesn't"} support an answer, it says so instead of guessing.</p>
            <div className="actions">
              <Link className="cta" to="/signup">Upload a contract</Link>
              <Link className="textlink" to="/demo">See it working &rarr;</Link>
            </div>
          </div>
        </section>

        {/* ===================== 2. WHAT IT CATCHES ===================== */}
        <section className="catches">
          <div className="wrap">
            <p className="eyebrow">What it catches</p>
            <h2 className="sec">Nine kinds of contract terms ClauseClock watches.</h2>
            <p className="lede">Most of these never make it onto a calendar, because nobody re-reads a signed agreement until something has already gone wrong.</p>

            <ul className="types">
              <li><span className="t">Renewal and non-renewal deadlines</span><span className="d">Auto-renewal dates and the last day to stop one</span></li>
              <li><span className="t">Notice requirements</span><span className="d">How much warning is owed, in what form, to whom</span></li>
              <li><span className="t">Price increases</span><span className="d">Scheduled uplifts, indexation, and caps on them</span></li>
              <li><span className="t">Termination rights</span><span className="d">When you may exit, for cause or for convenience</span></li>
              <li><span className="t">Fees and penalties</span><span className="d">Late charges, early-exit costs, minimum commitments</span></li>
              <li><span className="t">Rebates and refunds</span><span className="d">Money owed back to you, and the window to ask</span></li>
              <li><span className="t">Warranties</span><span className="d">Coverage periods and what voids them</span></li>
              <li><span className="t">Service credits</span><span className="d">Credits owed after service failures, and the window to claim them</span></li>
              <li><span className="t">Disputes</span><span className="d">Escalation steps and the time limits on each</span></li>
            </ul>
          </div>
        </section>

        {/* ===================== 3. THE EVIDENCE ===================== */}
        <section className="evidence-intro">
          <div className="wrap">
            <p className="eyebrow">A finding</p>
            <h2 className="sec">Every date traces back to the sentence that produced it.</h2>
            <p className="lede">Nothing below is summarised or restated. The clause is quoted as written, and each value is derived from it.</p>
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
            <div className="row"><dt>Notice counts back from</dt><dd>End of term</dd></div>
            <div className="row-note"><p>&ldquo;…not less than sixty (60) days prior to the end of the then-current term.&rdquo;</p></div>
            <div className="row"><dt>Notice period</dt><dd>60 days</dd></div>
            <div className="row result"><dt>Notice deadline</dt><dd>October 1, 2028</dd></div>
          </dl>

          <p className="derivation">The anchor is classified from the quoted phrase, then the date is computed in Python from that anchor. It is not inferred by a language model. ClauseClock asks you to confirm a finding before it starts tracking the date.</p>
        </article>

        {/* ===================== 4. HOW IT WORKS ===================== */}
        <section className="how">
          <div className="wrap">
            <p className="eyebrow">How it works</p>
            <h2 className="sec">Nothing gets tracked until you have seen where it came from.</h2>

            <ol className="steps">
              <li><span><span className="t">Upload your agreements</span><span className="d">Vendor contracts, amendments, and the signed versions of both</span></span></li>
              <li><span><span className="t">Findings surface with their source</span><span className="d">Each one carries the clause, the page, and the derivation</span></span></li>
              <li><span><span className="t">You verify before anything is tracked</span><span className="d">Confirm, correct, or dismiss — ClauseClock does not act on its own reading</span></span></li>
              <li><span><span className="t">The Action Center shows what is required</span><span className="d">What is owed, to whom, in what form, and by when</span></span></li>
              <li><span><span className="t">You log the action and attach evidence</span><span className="d">The notice you sent, fingerprinted when it is filed</span></span></li>
              <li><span><span className="t">The outcome is recorded</span><span className="d">A closed record of what the contract required and what you did</span></span></li>
            </ol>
          </div>
        </section>

        {/* ===================== 5. WHY THE DATES HOLD ===================== */}
        <section className="integrity">
          <div className="wrap">
            <p className="eyebrow">Why the dates hold</p>
            <h2 className="sec">A wrong date is worse than no date.</h2>

            <ul className="claims">
              <li>
                <span className="t">Dates are computed, not estimated.</span>
                <span className="d">Once the anchor and the notice period are read from the contract, the arithmetic runs in Python. The same inputs always produce the same date.</span>
              </li>
              <li>
                <span className="t">Every finding carries its source.</span>
                <span className="d">The clause is stored verbatim and matched against the document it came from, so you can check any value against the page it was read from.</span>
              </li>
              <li>
                <span className="t">Unclear contracts get a refusal, not a guess.</span>
                <span className="d">If the effective date is missing, or the language does not establish what the notice period counts back from, ClauseClock declines to produce a deadline and tells you what it needs.</span>
              </li>
            </ul>

            <p className="after"><Link className="textlink" to="/demo">See a refusal in the worked example &rarr;</Link></p>
          </div>
        </section>

        {/* ===================== 6. CLOSE ===================== */}
        <section className="close">
          <div className="wrap">
            <h2>Start with one contract.</h2>
            <p>Upload a vendor agreement and see what ClauseClock finds in it — and what it will not claim to know.</p>
            <Link className="cta" to="/signup">Upload a contract</Link>
            <p className="fineprint">ClauseClock is not a law firm and does not provide legal advice. All data and examples on this page are synthetic demonstration values.</p>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap">
          <p>ClauseClock</p>
          <p>Synthetic Demo Landing Page — V2 homepage</p>
        </div>
      </footer>
    </div>
  );
}
