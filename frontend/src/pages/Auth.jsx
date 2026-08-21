// Login / Signup — Stage 1 auth. Two registers of the design system: calm
// paper ground, ink type, single seal accent. No AI-SaaS gradient hero.
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Clock8 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { formatApiErrorDetail } from "@/lib/api";
import { Eyebrow } from "@/components/cc/Primitives";

export default function Auth({ mode = "login" }) {
  const isLogin = mode === "login";
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isLogin) await login(email, password);
      else await register(email, password);
      navigate("/app");
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8">
          <Clock8 className="h-5 w-5 text-seal" strokeWidth={2.25} />
          <span className="font-archivo-expanded font-bold tracking-tight text-[18px] uppercase text-ink">
            ClauseClock
          </span>
        </div>

        <Eyebrow>{isLogin ? "Sign in" : "Create account"}</Eyebrow>
        <div className="cc-seal-rule mt-3 mb-4" />
        {isLogin && (
          <>
            <p className="cc-days-remaining mb-4 max-w-sm" data-testid="auth-product-line">
              ClauseClock finds renewal and pricing terms, verifies them against the original
              contract language, and helps you act before the deadline.
            </p>
            <Link to="/demo" data-testid="auth-see-demo"
              className="inline-block cc-days-remaining text-seal underline underline-offset-2 mb-6">
              See it working →
            </Link>
          </>
        )}

        <form onSubmit={submit} className="space-y-5" data-testid="auth-form">
          <div className="space-y-2">
            <Label htmlFor="email" className="cc-eyebrow">Email</Label>
            <Input
              id="email" type="email" required value={email}
              data-testid="auth-email"
              onChange={(e) => setEmail(e.target.value)}
              className="bg-card border-rule h-11"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="cc-eyebrow">Password</Label>
            <Input
              id="password" type="password" required value={password}
              data-testid="auth-password"
              onChange={(e) => setPassword(e.target.value)}
              className="bg-card border-rule h-11"
            />
          </div>

          {error && (
            <p data-testid="auth-error" className="cc-days-remaining text-stamp">
              {error}
            </p>
          )}

          <Button
            type="submit" disabled={busy} data-testid="auth-submit"
            className="w-full bg-ink text-paper hover:bg-ink/90 rounded-full h-11"
          >
            {busy ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className="cc-days-remaining mt-6">
          {isLogin ? (
            <>New here?{" "}
              <Link to="/signup" className="text-seal underline underline-offset-2" data-testid="auth-switch-signup">
                Create an account
              </Link>
            </>
          ) : (
            <>Already have an account?{" "}
              <Link to="/login" className="text-seal underline underline-offset-2" data-testid="auth-switch-login">
                Sign in
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
