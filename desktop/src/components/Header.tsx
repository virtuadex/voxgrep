import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Zap, Activity, Terminal } from "lucide-react";

interface HeaderProps {
  message?: string | null;
}

export function Header({ message }: HeaderProps) {
  return (
    <header className="flex justify-between items-start relative">
      {/* Left: Brand */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="flex flex-col"
      >
        <div className="flex items-center gap-4">
          {/* Logo Mark */}
          <div className="relative">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-accent-primary to-orange-600 flex items-center justify-center shadow-lg shadow-accent-primary/25">
              <Zap className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-accent-success rounded-full border-2 border-bg-main flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
            </div>
          </div>
          
          {/* Logo Type */}
          <div>
            <h1 className="text-3xl font-black text-text-primary tracking-tight leading-none">
              VOX<span className="text-accent-primary">GREP</span>
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="tech-label text-text-muted">DIALOG ENGINE</span>
              <span className="w-1 h-1 rounded-full bg-border-strong" />
              <span className="tech-label text-accent-success flex items-center gap-1">
                <Activity className="w-2.5 h-2.5" />
                ACTIVE
              </span>
            </div>
          </div>
        </div>

        {/* Status Message */}
        <AnimatePresence>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 glass-card rounded-lg"
            >
              <div className="w-5 h-5 rounded-full bg-accent-success/20 flex items-center justify-center">
                <CheckCircle2 className="w-3 h-3 text-accent-success" />
              </div>
              <span className="text-sm font-medium text-text-primary">{message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Right: System Info */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        className="flex items-center gap-4"
      >
        {/* Version Badge */}
        <div className="glass-card rounded-lg px-4 py-2 flex items-center gap-3">
          <Terminal className="w-4 h-4 text-text-muted" />
          <div>
            <div className="tech-label text-text-muted">Build</div>
            <div className="text-sm font-mono font-semibold text-text-primary">v0.3.0</div>
          </div>
        </div>

        {/* Connection Status */}
        <div className="glass-card rounded-lg px-4 py-2 flex items-center gap-3">
          <div className="status-dot status-online" />
          <div>
            <div className="tech-label text-text-muted">Backend</div>
            <div className="text-sm font-mono font-semibold text-accent-success">Connected</div>
          </div>
        </div>
      </motion.div>
    </header>
  );
}
