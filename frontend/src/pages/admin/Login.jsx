import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Hexagon, Lock, Phone, ArrowRight, Eye, EyeOff } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import toast from "react-hot-toast";
import { useAuthStore } from "../../store/authStore";
import Button from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import Hero3D from "../../three/Hero3D";
import { fadeUp } from "../../motion/reveal";
import { formatUzPhone, normalizeUzPhone } from "../../lib/phone";

export default function Login() {
  const [phone, setPhone] = useState("+998 ");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(normalizeUzPhone(phone), password);
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Telefon raqam yoki parol noto'g'ri");
    } finally {
      setLoading(false);
    }
  }

  const motionProps = (i) =>
    prefersReducedMotion ? {} : { custom: i, initial: "hidden", animate: "visible", variants: fadeUp };

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
            className="glass-dark space-y-5 rounded-[28px] p-6 elevation-lg sm:p-8"
          >
            <div className="mb-2 hidden lg:block">
              <h2 className="font-display text-2xl font-semibold text-white">
                Xush kelibsiz <span className="text-gradient">qaytib</span>
              </h2>
              <p className="mt-1 text-sm text-white/50">Telefon raqamingiz bilan tizimga kiring</p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-white/75">Telefon raqami</label>
              <div>
                <Input
                  appearance="dark"
                  leadingIcon={<Phone size={16} />}
                  type="tel"
                  inputMode="numeric"
                  value={phone}
                  onChange={(e) => setPhone(formatUzPhone(e.target.value))}
                  placeholder="+998 90 123 45 67"
                  autoComplete="tel"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-white/75">Parol</label>
              <div>
                <Input
                  appearance="dark"
                  leadingIcon={<Lock size={16} />}
                  trailing={
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      magnetic={false}
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                      className="!rounded-lg !border-transparent !bg-transparent !text-white/40 hover:!bg-transparent hover:!text-white/70"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </Button>
                  }
                  type={showPassword ? "text" : "password"}
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
            <a href="/terminal/login" className="-m-2 inline-flex min-h-11 items-center rounded-lg p-2 font-semibold text-(--accent-bright) underline">
              Terminal login
            </a>
          </motion.p>
        </div>
      </div>
    </div>
  );
}
