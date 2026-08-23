// AppShell — the three-destination layout (PART 5.6): Dashboard · Contracts ·
// Action Center, plus one primary action, Add contract. No sidebar.
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Clock8, Plus, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { NAV } from "@/constants/testIds";
import { LegalFooter } from "@/components/cc/Primitives";
import { useAuth } from "@/context/AuthContext";

const navItem = ({ isActive }) =>
  cn(
    "cc-eyebrow px-1 py-2 transition-colors duration-150 border-b-2 -mb-px",
    isActive
      ? "text-ink border-seal"
      : "text-ink-soft border-transparent hover:text-ink"
  );

export const AppShell = ({ demo = false }) => {
  const navigate = useNavigate();
  const auth = useAuth();
  const base = demo ? "/demo" : "/app";

  return (
    <div className="min-h-screen flex flex-col bg-paper">
      <header className="border-b border-rule bg-paper/90 backdrop-blur-sm sticky top-0 z-40">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between py-3 md:py-0 md:h-16 gap-3 md:gap-4">
            <div className="flex items-center gap-3">
              <NavLink
                to={base}
                data-testid={NAV.brand}
                className="flex items-center gap-2 text-ink shrink-0"
              >
                <Clock8 className="h-5 w-5 text-seal" strokeWidth={2.25} />
                <span className="font-archivo-expanded font-bold tracking-tight text-[18px] uppercase">
                  ClauseClock
                </span>
              </NavLink>
              {demo && (
                <span className="cc-eyebrow ml-2 hidden sm:inline shrink-0">
                  Synthetic demo workspace
                </span>
              )}
            </div>

            <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 justify-start md:justify-end w-full md:w-auto">
              <NavLink end to={base} className={navItem} data-testid={NAV.dashboard}>
                Dashboard
              </NavLink>
              <NavLink
                to={`${base}/contracts`}
                className={navItem}
                data-testid={NAV.contracts}
              >
                Contracts
              </NavLink>
              <NavLink
                to={`${base}/actions`}
                className={navItem}
                data-testid={NAV.actionCenter}
              >
                Action Center
              </NavLink>
              {!demo && (
                <Button
                  size="sm"
                  data-testid={NAV.addContract}
                  onClick={() => navigate("/app/upload")}
                  className="bg-ink text-paper hover:bg-ink/90 rounded-full h-8 px-3 gap-1 text-xs md:h-9 md:px-4 md:gap-1.5 md:text-sm shrink-0"
                >
                  <Plus className="h-3 w-3 md:h-4 md:w-4" strokeWidth={2.5} />
                  Add contract
                </Button>
              )}
              {!demo && auth?.user && (
                <button
                  data-testid="nav-logout"
                  onClick={async () => {
                    await auth.logout();
                    navigate("/login");
                  }}
                  className="cc-eyebrow text-ink-soft hover:text-ink transition-colors flex items-center gap-1.5 shrink-0"
                  title="Sign out"
                >
                  <LogOut className="h-4 w-4" strokeWidth={2} />
                </button>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-6 py-14 animate-cc-settle">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <LegalFooter className="max-w-2xl" />
        </div>
      </footer>
    </div>
  );
};
