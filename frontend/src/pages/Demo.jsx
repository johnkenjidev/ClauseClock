// /demo — public, read-only synthetic ClauseClock mockup-based workspace.
import { useState, useEffect } from "react";
import { DEMO } from "@/constants/testIds";

export default function Demo() {
  const [theme, setTheme] = useState("dark");
  const [drawerOpen, setDrawerOpen] = useState(true);

  useEffect(() => {
    // Hide standard AppShell layout header and footer dynamically
    const header = document.querySelector("header");
    const footer = document.querySelector("footer");
    if (header) header.style.display = "none";
    if (footer) footer.style.display = "none";

    document.body.setAttribute("data-theme", "dark");

    return () => {
      if (header) header.style.display = "";
      if (footer) footer.style.display = "";
      document.body.removeAttribute("data-theme");
    };
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.body.setAttribute("data-theme", next);
  };

  return (
    <div data-testid={DEMO.root} className="demo-wrapper-v2 min-h-screen">
      <style dangerouslySetInnerHTML={{ __html: `
        /* Override standard AppShell container to match mockup full bleed */
        header { display: none !important; }
        footer { display: none !important; }
        main.flex-1 > div.mx-auto.max-w-6xl.px-6.py-14 {
          max-width: 100% !important;
          padding: 0 !important;
        }

        :root, [data-theme="dark"]{
          /* near-black with a faint green cast — ties to the seal, avoids default slate */
          --paper:#101412; --card:#171C19; --rule:#28302B;
          --ink:#E9E7E1; --ink-soft:#939B95;
          /* the drawer is the ONLY light surface: a document under a lamp */
          --document:#E6E1D6; --document-ink:#1A1D21; --document-soft:#5A5F58; --document-rule:#CFC8B9;
          --seal:#4FA97C; --stamp:#E0603C; --pending:#C89A3C;
          --drawer-glow:0 0 0 1px rgba(230,225,214,.14), 0 -8px 40px rgba(230,225,214,.07);
        }
        [data-theme="light"]{
          --paper:#FAFAF8; --card:#FFFFFF; --rule:#E4E2DB;
          --ink:#1A1D21; --ink-soft:#545A62;
          --document:#F4F2EC; --document-ink:#1A1D21; --document-soft:#545A62; --document-rule:#E4E2DB;
          --seal:#1F6B4A; --stamp:#B3411F; --pending:#8A6410;
          --drawer-glow:none;
        }
        .demo-wrapper-v2 {
          background: var(--paper);
          color: var(--ink);
          font-family: 'Archivo', system-ui, sans-serif;
          font-variant-numeric: tabular-nums;
          -webkit-font-smoothing: antialiased;
          min-height: 100vh;
        }
        .demo-wrapper-v2 .mono{font-family:'IBM Plex Mono',monospace}
        .demo-wrapper-v2 .eyebrow{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft)}

        /* ---- top bar ---- */
        .demo-header{
          border-bottom:1px solid var(--rule); background:var(--card);
          position:sticky;top:0;z-index:10;
        }
        .demo-bar{max-width:1080px;margin:0 auto;padding:0 32px;height:64px;display:flex;align-items:center;gap:40px}
        .demo-wordmark{font-weight:700;font-size:17px;letter-spacing:-.01em;display:flex;align-items:center;gap:9px;color:var(--ink)}
        .demo-dial{width:16px;height:16px;border:2px solid var(--ink);border-radius:50%;position:relative}
        .demo-dial::after{content:"";position:absolute;left:50%;top:2px;width:1.5px;height:5px;background:var(--ink);transform-origin:bottom;transform:translateX(-50%)}
        .demo-nav{display:flex;gap:28px;margin-left:8px}
        .demo-nav a{
          text-decoration:none;color:var(--ink-soft);font-size:14px;font-weight:500;
          padding:22px 0;border-bottom:2px solid transparent;
        }
        .demo-nav a.on{color:var(--ink);border-bottom-color:var(--ink)}
        .demo-right{margin-left:auto;display:flex;align-items:center;gap:18px}
        .demo-synthetic{
          font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
          color:var(--ink-soft);border:1px solid var(--rule);
          padding:5px 10px;border-radius:3px;background:var(--card);
        }
        .demo-toggle{
          background:none;border:1px solid var(--rule);color:var(--ink-soft);border-radius:4px;
          padding:8px 12px;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;
        }
        .demo-toggle:hover{color:var(--ink)}
        .demo-add{
          background:var(--ink);color:var(--paper);border:none;border-radius:4px;
          padding:9px 15px;font-family:inherit;font-size:13.5px;font-weight:600;cursor:pointer;
        }

        .demo-main{max-width:1080px;margin:0 auto;padding:44px 32px 100px}

        /* ---- attention line ---- */
        .demo-attention{padding-bottom:28px;border-bottom:1px solid var(--rule);margin-bottom:36px}
        .demo-attention h1{font-size:27px;font-weight:600;letter-spacing:-.02em;line-height:1.25;color:var(--ink)}
        .demo-attention p{margin-top:7px;font-size:14.5px;color:var(--ink-soft)}

        /* ---- the urgent finding ---- */
        .demo-finding{
          background:var(--card);border:1px solid var(--rule);border-radius:6px;
          overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.28);
        }
        .demo-finding-head{display:flex;gap:36px;padding:28px 30px 24px}
        .demo-date-block{flex-shrink:0;width:172px;border-right:1px solid var(--rule);padding-right:32px}
        .demo-hero-date{
          font-family:'Archivo Expanded','Archivo',sans-serif;font-weight:700;
          font-size:50px;line-height:.94;letter-spacing:-.02em;text-transform:uppercase;
          color:var(--stamp);
        }
        .demo-hero-year{font-size:14px;font-weight:500;color:var(--ink-soft);margin-top:8px}
        .demo-days{margin-top:14px;font-size:14.5px;font-weight:600;color:var(--stamp)}
        .demo-summary{flex:1;min-width:0}
        .demo-tagline{display:flex;align-items:center;gap:10px;margin-bottom:11px}
        .demo-chip{
          font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
          padding:3px 7px;border-radius:2.5px;background:var(--stamp);color:#12100E;
        }
        .demo-counterparty{font-size:12.5px;color:var(--ink-soft)}
        .demo-summary h2{font-size:19.5px;font-weight:600;letter-spacing:-.01em;margin-bottom:11px;color:var(--ink)}
        .demo-plain{font-size:16px;line-height:1.6;max-width:56ch;color:var(--ink)}
        .demo-matters{
          margin-top:15px;padding-left:14px;border-left:2px solid var(--rule);
          font-size:15px;line-height:1.55;color:var(--ink-soft);max-width:56ch;
        }
        .demo-matters strong{color:var(--ink);font-weight:600}

        .demo-facts{
          display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
          background:var(--rule);border-top:1px solid var(--rule);
        }
        .demo-fact{background:var(--card);padding:15px 22px}
        .demo-fact .eyebrow{display:block;margin-bottom:5px}
        .demo-fact .v{font-size:14.5px;font-weight:600;color:var(--ink)}
        .demo-fact .v.soft{font-weight:500;color:var(--ink-soft)}

        /* ---- clause drawer ---- */
        .demo-drawer-toggle{
          width:100%;background:var(--card);border:none;border-top:1px solid var(--rule);
          padding:13px 30px;text-align:left;cursor:pointer;
          font-family:inherit;font-size:13px;font-weight:600;color:var(--ink-soft);
          display:flex;align-items:center;gap:8px;
        }
        .demo-drawer-toggle:hover{color:var(--ink)}
        .demo-drawer{
          background:var(--document);color:var(--document-ink);
          border-top:1px solid var(--rule);padding:26px 30px 28px;
          box-shadow:var(--drawer-glow);position:relative;
        }
        .demo-drawer-note{font-size:12.5px;color:var(--document-soft);margin-bottom:20px;max-width:60ch;line-height:1.5}
        .demo-clause{display:flex;gap:26px;padding:17px 0;border-top:1px solid var(--document-rule)}
        .demo-clause:first-of-type{border-top:none;padding-top:0}
        .demo-clause-rail{width:158px;flex-shrink:0}
        .demo-clause-rail .p{display:block;font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--document-ink);margin-bottom:5px}
        .demo-clause-rail .ref{font-family:'IBM Plex Mono',monospace;font-size:11.5px;font-weight:500;color:var(--document-soft)}
        .demo-quote{
          font-family:'IBM Plex Mono',monospace;font-size:13.5px;line-height:1.72;
          color:var(--document-ink);max-width:64ch;
        }
        .demo-verified{
          margin-top:22px;padding-top:16px;border-top:1px solid var(--document-rule);
          display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--document-soft);
        }
        .demo-tick{width:14px;height:14px;flex-shrink:0;color:#1F6B4A}

        /* ---- actions ---- */
        .demo-actions{display:flex;gap:10px;padding:18px 30px;border-top:1px solid var(--rule);align-items:center}
        .demo-btn{
          font-family:inherit;font-size:13.5px;font-weight:600;padding:10px 16px;
          border-radius:4px;cursor:pointer;border:1px solid var(--rule);background:var(--card);color:var(--ink);
        }
        .demo-btn.primary{background:var(--ink);color:var(--paper);border-color:var(--ink)}
        .demo-conf{margin-left:auto;font-size:12px;color:var(--ink-soft);display:flex;align-items:center;gap:7px}
        .demo-dot{width:7px;height:7px;border-radius:50%;background:var(--seal)}

        /* ---- everything else ---- */
        .demo-section-head{
          display:flex;align-items:baseline;justify-content:space-between;
          margin:46px 0 4px;padding-bottom:11px;border-bottom:1px solid var(--rule);
        }
        .demo-section-head h3{font-size:15px;font-weight:600;color:var(--ink)}
        .demo-section-head a{font-size:13px;color:var(--ink-soft);text-decoration:none}
        .demo-row{
          display:flex;align-items:center;gap:20px;padding:15px 4px;
          border-bottom:1px solid var(--rule);cursor:pointer;
        }
        .demo-row:hover{background:var(--card)}
        .demo-row-date{width:96px;flex-shrink:0}
        .demo-row-date .d{font-size:15px;font-weight:600;letter-spacing:-.01em;color:var(--ink)}
        .demo-row-date .r{font-size:12px;color:var(--ink-soft);margin-top:2px}
        .demo-row-date.pending .d{color:var(--pending)}
        .demo-row-main{flex:1;min-width:0}
        .demo-row-main .t{font-size:14.5px;font-weight:600;margin-bottom:2px;color:var(--ink)}
        .demo-row-main .s{font-size:13px;color:var(--ink-soft);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .demo-tag{
          font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
          padding:3px 6px;border-radius:2.5px;flex-shrink:0;
          border:1px solid var(--rule);color:var(--ink-soft);background:var(--card);
        }
        .demo-tag.money{color:var(--seal);border-color:color-mix(in srgb, var(--seal) 34%, transparent)}
        .demo-tag.pending{color:var(--pending);border-color:color-mix(in srgb, var(--pending) 34%, transparent)}
        .demo-row-val{width:104px;text-align:right;font-size:14px;font-weight:600;flex-shrink:0;color:var(--ink)}
        .demo-row-val.soft{font-weight:500;color:var(--ink-soft)}

        /* ---- portfolio strip ---- */
        .demo-portfolio{
          margin-top:52px;padding-top:26px;border-top:2px solid var(--ink-soft);
          display:grid;grid-template-columns:repeat(4,1fr);gap:34px;
        }
        .demo-stat .eyebrow{display:block;margin-bottom:9px}
        .demo-stat .n{font-size:25px;font-weight:600;letter-spacing:-.02em;color:var(--ink)}
        .demo-stat .sub{font-size:12.5px;color:var(--ink-soft);margin-top:4px}
        .demo-stat .n.seal{color:var(--seal)}

        .demo-footer{
          max-width:1080px;margin:0 auto;padding:0 32px 64px;
          font-size:12px;line-height:1.6;color:var(--ink-soft);max-width:72ch;
        }

        @media (max-width:860px){
          .demo-bar{gap:16px;padding:0 20px} .demo-synthetic{display:none}
          .demo-main{padding:28px 20px 72px}
          .demo-finding-head{flex-direction:column;gap:22px;padding:22px}
          .demo-date-block{width:auto;border-right:none;border-bottom:1px solid var(--rule);padding:0 0 18px}
          .demo-facts{grid-template-columns:1fr 1fr}
          .demo-clause{flex-direction:column;gap:8px} .demo-clause-rail{width:auto}
          .demo-drawer,.demo-actions{padding-left:22px;padding-right:22px}
          .demo-portfolio{grid-template-columns:1fr 1fr;gap:26px}
          .demo-row-val{display:none}
        }
      ` }} />

      <header className="demo-header">
        <div className="demo-bar">
          <div className="demo-wordmark"><span className="demo-dial"></span>ClauseClock</div>
          <nav className="demo-nav">
            <a href="#" className="on">Dashboard</a>
            <a href="#">Contracts</a>
            <a href="#">Action Center</a>
          </nav>
          <div className="demo-right">
            <span className="demo-synthetic">Synthetic demo workspace</span>
            <button className="demo-toggle" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === "dark" ? "Light" : "Dark"}
            </button>
            <button className="demo-add">Add contract</button>
          </div>
        </div>
      </header>

      <main className="demo-main">
        <div className="demo-attention">
          <h1>One window needs action.</h1>
          <p>14 contracts monitored · everything else is more than 40 days out · Synthetic Demo Mode</p>
        </div>

        <article className="demo-finding">
          <div className="demo-finding-head">
            <div className="demo-date-block">
              <div className="demo-hero-date">Sep 2</div>
              <div className="demo-hero-year">2026</div>
              <div className="demo-days">13 days remaining</div>
            </div>
            <div className="demo-summary">
              <div className="demo-tagline">
                <span className="demo-chip">Automatic renewal</span>
                <span className="demo-counterparty">Acme Cloud Services, Inc.</span>
              </div>
              <h2>Master Services Agreement</h2>
              <p className="demo-plain">This agreement renews for another 12 months on 1 December unless you give written notice at least 90 days beforehand.</p>
              <p className="demo-matters">Another term is valued at <strong>$24,000</strong>. Notice must be <strong>received</strong> by 2 September — email is not accepted for non-renewal.</p>
            </div>
          </div>

          <div className="demo-facts">
            <div className="demo-fact"><span className="eyebrow">Next renewal</span><span className="demo-v">1 Dec 2026</span></div>
            <div className="demo-fact"><span className="eyebrow">Notice period</span><span className="demo-v">90 days</span></div>
            <div className="demo-fact"><span className="eyebrow">Method required</span><span className="demo-v">Certified mail</span></div>
            <div className="demo-fact"><span className="eyebrow">Addressed to</span><span className="demo-v soft">General Counsel</span></div>
          </div>

          <button className="demo-drawer-toggle" onClick={() => setDrawerOpen(!drawerOpen)}>
            {drawerOpen ? "Hide the contract language ⌃" : "Show the contract language ⌄"}
          </button>

          {drawerOpen && (
            <div className="demo-drawer animate-cc-settle">
              <p className="demo-drawer-note">Three clauses from two pages, assembled into one deadline. Each quote below was matched verbatim against the uploaded document.</p>

              <div className="demo-clause">
                <div className="demo-clause-rail">
                  <span className="p">Renewal term</span>
                  <span className="ref">§8.2 · p.22</span>
                </div>
                <p className="demo-quote">“This Agreement shall automatically renew for successive one (1) year periods unless either party provides written notice of non-renewal.”</p>
              </div>

              <div className="demo-clause">
                <div className="demo-clause-rail">
                  <span className="p">Notice period</span>
                  <span className="ref">§8.2 · p.22</span>
                </div>
                <p className="demo-quote">“…such notice to be received not less than ninety (90) days prior to the expiration of the then-current term.”</p>
              </div>

              <div className="demo-clause">
                <div className="demo-clause-rail">
                  <span className="p">Notice method</span>
                  <span className="ref">§12.4 · p.23</span>
                </div>
                <p className="demo-quote">“All notices of termination or non-renewal shall be delivered by certified mail, return receipt requested, to the General Counsel at the address set forth below. Electronic mail shall not constitute valid notice under this Section.”</p>
              </div>

              <div className="demo-verified">
                <svg className="demo-tick" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 8.5l3.2 3.2L13 5"/></svg>
                All 3 quotes verified against Acme_MSA_2024.pdf · deadline computed from the notice period, not estimated
              </div>
            </div>
          )}

          <div className="demo-actions">
            <button className="demo-btn primary">Confirm deadline</button>
            <button className="demo-btn">Correct</button>
            <button className="demo-btn">Dismiss</button>
            <span className="demo-conf"><span className="demo-dot"></span>High confidence</span>
          </div>
        </article>

        <div className="demo-section-head">
          <h3>Upcoming</h3>
          <a href="#">View all findings →</a>
        </div>

        <div className="demo-row">
          <div className="demo-row-date pending"><div className="d">15 Oct</div><div className="r">56 days</div></div>
          <div className="demo-row-main"><div className="t">Northwind Logistics — Services Agreement</div><div className="demo-row-val md:hidden">$41,000</div><div className="demo-row-val soft sm:hidden">$41,000</div><div className="s">Objection window · vendor may increase fees by up to 6%</div></div>
          <span className="demo-tag money">Money</span>
          <div className="demo-row-val">$41,000</div>
        </div>

        <div className="demo-row">
          <div className="demo-row-date"><div className="d">3 Nov</div><div className="r">75 days</div></div>
          <div className="demo-row-main"><div className="t">Kestrel Data — Subscription Agreement</div><div className="demo-row-val md:hidden">$8,400</div><div className="demo-row-val soft sm:hidden">$8,400</div><div className="s">Automatic renewal · 30 days written notice</div></div>
          <span className="demo-tag">Renewal</span>
          <div className="demo-row-val">$8,400</div>
        </div>

        <div className="demo-row">
          <div className="demo-row-date"><div className="d">—</div><div className="r">no date</div></div>
          <div className="demo-row-main"><div className="t">Pemberton Facilities — Master Agreement</div><div className="demo-row-val md:hidden">$16,200</div><div className="demo-row-val soft sm:hidden">$16,200</div><div className="s">Effective date not stated in the document — confirm it to calculate this deadline</div></div>
          <span className="demo-tag pending">Needs review</span>
          <div className="demo-row-val soft">$16,200</div>
        </div>

        <div className="demo-row">
          <div className="demo-row-date"><div className="d">12 Jan</div><div className="r">145 days</div></div>
          <div className="demo-row-main"><div className="t">Halden Systems — Enterprise Licence</div><div className="demo-row-val md:hidden">$52,000</div><div className="demo-row-val soft sm:hidden">$52,000</div><div className="s">Automatic renewal · 60 days written notice</div></div>
          <span className="demo-tag">Renewal</span>
          <div className="demo-row-val">$52,000</div>
        </div>

        <section className="demo-portfolio">
          <div className="demo-stat">
            <span className="eyebrow">Contracts monitored</span>
            <div className="demo-stat n">14</div>
            <div className="sub">2 need review</div>
          </div>
          <div className="demo-stat">
            <span className="eyebrow">Value under tracking</span>
            <div className="demo-stat n">$186,400</div>
            <div className="sub">annual contract value</div>
          </div>
          <div className="demo-stat">
            <span className="eyebrow">Confirmed protected</span>
            <div className="demo-stat n seal">$18,000</div>
            <div className="sub">1 renewal term avoided</div>
          </div>
          <div className="demo-stat">
            <span className="eyebrow">Windows missed</span>
            <div className="demo-stat n">0</div>
            <div className="sub">since you started</div>
          </div>
        </section>
      </main>

      <footer className="demo-footer">
        <p>ClauseClock identifies possible obligations and rights from your documents. Verify against the original contract before acting. This is not legal advice. All data and metrics on this page are synthetic demonstration workspace values.</p>
      </footer>
    </div>
  );
}
