import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Button from "../components/ui/Button";

export default function NotFound() {
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 text-(--ink-soft)">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(36rem 28rem at 30% 20%, rgba(99,102,241,0.14), transparent 60%), radial-gradient(30rem 24rem at 76% 78%, rgba(124,58,237,0.12), transparent 60%)",
        }}
      />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel relative rounded-3xl px-6 py-8 text-center elevation-lg sm:px-10 sm:py-9"
      >
        <p className="page-title text-6xl font-bold leading-none text-gradient sm:text-7xl">404</p>
        <p className="mb-6 mt-3 text-(--ink-soft)">Sahifa topilmadi</p>
        <Button as={Link} to="/" magnetic={false} className="text-white!">
          <ArrowLeft size={16} /> Bosh sahifaga qaytish
        </Button>
      </motion.div>
    </div>
  );
}
