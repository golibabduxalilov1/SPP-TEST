import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Hexagon, Lock, User, ArrowRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import toast from "react-hot-toast";
import { useAuthStore } from "../../store/authStore";
import Button from "../../components/ui/Button";
import Hero3D from "../../three/Hero3D";
import { fadeUp } from "../../motion/reveal";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login yoki parol noto'g'ri");
    } finally {
      setLoading(false);
    }
  }

  const motionProps = (i) =>
    prefersReducedMotion ? {} : { custom: i, initial: "hidden", animate: "visible", variants: fadeUp };

  const darkInput =
    "w-full rounded-lg border border-white/10 bg-white/[0.06] pl-10 pr-3.5 py-3 text-[15px] text-white " +
    "placeholder:text-white/35 transition-[border-color,box-shadow,background-color] duration-200 " +
    "hover:border-white/20 focus:outline-none focus:border-[var(--accent-bright)] " +
    "focus:shadow-[0_0_0_3px_rgba(99,102,241,0.30)]";

  return (
    <div className="brand-shell grain relative min-h-dvh overflow-hidden flex items-center justify-center px-4 py-10 lg:px-0">
      <Hero3D variant="dark" className="opacity-90" subtle />
      <div className="surface-noise pointer-events-none absolute inset-0 opacity-[0.15]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_-10%,transparent,rgba(7,8,22,0.55))]" />

      <div className="relative z-10 grid w-full max-w-5xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        <motion.div {...motionProps(0)} className="hidden lg:block">
          <div className="mb-7 inline-flex items-center gap-2.5 rounded-full border border-white/10 bg-white/6 px-4 py-2 text-xs font-semibold tracking-wide text-white/70 backdrop-blur-md">
            <Hexagon size={15} className="text-(--accent-bright)" /> Silknode Production Platform
          </div>
          <h1 className="page-title text-[clamp(2.75rem,5vw,4.5rem)] font-semibold leading-[1.02] text-white">
            Har bir <span className="text-gradient">detal</span>
            <br />
            o'z yo'lini biladi.
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-white/55">
            Tsexdan omborgacha — buyurtmalar, stanoklar va xodimlar bitta
            aqlli boshqaruv panelida, real vaqtda.
          </p>
          <div className="mt-8 flex items-center gap-6 text-white/45">
            {[
              ["QR", "kuzatuv"],
              ["Offline", "terminal"],
              ["Real-time", "tablo"],
            ].map(([a, b]) => (
              <div key={a}>
                <p className="font-display text-lg font-semibold text-white/80">{a}</p>
                <p className="text-xs">{b}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <div className="w-full max-w-md justify-self-center lg:justify-self-end">
          <motion.div {...motionProps(1)} className="mb-8 flex flex-col items-center lg:hidden">
            <div className="mb-4 rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-4 text-white elevation-accent">
              <Hexagon size={30} />
            </div>
            <h1 className="page-title text-3xl font-semibold text-white">SPP</h1>
            <p className="mt-1 text-sm text-white/50">Silknode Production Platform — admin panel</p>
          </motion.div>

          <motion.form
            {...motionProps(2)}
            onSubmit={handleSubmit}
            className="glass-dark space-y-5 rounded-[28px] p-8 elevation-lg"
          >
            <div className="mb-2 hidden lg:block">
              <h2 className="font-display text-2xl font-semibold text-white">
                Xush kelibsiz <span className="text-gradient">qaytib</span>
              </h2>
              <p className="mt-1 text-sm text-white/50">Admin sifatida tizimga kiring</p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-white/75">Login</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  className={darkInput}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-white/75">Parol</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  className={darkInput}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            <Button type="submit" className="w-full" size="lg" disabled={loading} loading={loading}>
              Kirish <ArrowRight size={18} />
            </Button>
          </motion.form>

          <motion.p {...motionProps(3)} className="mt-6 text-center text-xs text-white/40">
            Tsex terminali kerakmi?{" "}
            <a href="/terminal/login" className="font-semibold text-(--accent-bright) underline">
              Terminal login
            </a>
          </motion.p>
        </div>
      </div>
    </div>
  );
}
