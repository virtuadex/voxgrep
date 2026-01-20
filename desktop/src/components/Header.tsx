import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2 } from "lucide-react";

interface HeaderProps {
  message?: string | null;
}

export function Header({ message }: HeaderProps) {
  return (
    <header className="mb-12 flex justify-between items-start">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-5xl font-black text-text-main tracking-tighter mix-blend-multiply">
          VOXGREP
        </h1>
        <div className="flex items-center gap-4 mt-2">
          <div className="flex items-center gap-2 px-3 py-1 bg-white border border-border-main rounded-sm shadow-sm">
            <div className="w-2 h-2 rounded-full bg-accent-orange" />
            <p className="technical-text text-text-muted">
              System Online
            </p>
          </div>
          
          <AnimatePresence>
            {message && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 5 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: -5 }}
                className="flex items-center gap-2 px-3 py-1 bg-accent-blue text-white technical-text rounded-sm shadow-md"
              >
                <CheckCircle2 size={12} />
                {message}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
      <div className="text-right">
        <div className="technical-text text-text-muted mb-1">Build Version</div>
        <div className="text-xs font-mono text-text-main bg-bg-secondary px-2 py-1 border border-border-main">
          v0.2.0-alpha
        </div>
      </div>
    </header>
  );
}
