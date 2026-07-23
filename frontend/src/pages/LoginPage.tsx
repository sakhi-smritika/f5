import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion, type Variants } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { AppLogo } from '../components/AppLogo'
import { APP_NAME } from '../lib/brand'
import { MemoryField } from './login/MemoryField'
import './LoginPage.css'

const container: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.1, delayChildren: 0.15 },
  },
}

const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 260, damping: 24 },
  },
}

export function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      await signIn(email, password)
      // Brief success beat before leaving the screen.
      setSuccess(true)
      setTimeout(() => navigate(from, { replace: true }), 650)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed')
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <MemoryField />
      <div className="login-aurora" aria-hidden="true" />

      <motion.section
        className="login-card"
        variants={container}
        initial="hidden"
        animate="show"
      >
        <motion.div className="login-brand" variants={rise}>
          <span className="login-logo-halo">
            <AppLogo size={56} />
          </span>
          <h1>{APP_NAME}</h1>
        </motion.div>

        <motion.p className="login-subtitle" variants={rise}>
          A companion who remembers. Sign in to continue.
        </motion.p>

        <motion.form onSubmit={handleSubmit} variants={rise}>
          <motion.div className="login-field" variants={rise}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </motion.div>

          <motion.div className="login-field" variants={rise}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </motion.div>

          <AnimatePresence>
            {error ? (
              <motion.p
                className="login-error"
                key="error"
                initial={{ opacity: 0, height: 0 }}
                animate={{
                  opacity: 1,
                  height: 'auto',
                  x: [0, -8, 8, -6, 6, 0],
                }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ x: { duration: 0.4 }, default: { duration: 0.2 } }}
              >
                {error}
              </motion.p>
            ) : null}
          </AnimatePresence>

          <motion.button
            type="submit"
            variants={rise}
            disabled={submitting}
            className={success ? 'is-success' : undefined}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.97 }}
          >
            <AnimatePresence mode="wait" initial={false}>
              {success ? (
                <motion.span
                  key="done"
                  initial={{ opacity: 0, scale: 0.6 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  Welcome back
                </motion.span>
              ) : submitting ? (
                <motion.span
                  key="loading"
                  className="login-loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <span className="login-spinner" />
                  Signing in
                </motion.span>
              ) : (
                <motion.span
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  Sign in
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </motion.form>
      </motion.section>
    </main>
  )
}
