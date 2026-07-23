import { useEffect, useRef } from 'react'
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion'

/**
 * "The Field of Memory" — the animated backdrop for the login screen.
 *
 * It renders three brand ideas onto a single full-viewport canvas:
 *   1. Memory motes    — drifting glowing particles that leave fading trails
 *                        (memory persisting) and connect to nearby motes.
 *   2. The companion   — a soft central orb that gently breathes.
 *   3. The loop        — four points slowly orbiting the orb:
 *                        Reflect - Understand - Intend - Learn.
 *
 * The motes lean toward the cursor (a companion that notices you). When the
 * user prefers reduced motion, a single calm static frame is drawn instead.
 */

type Mote = {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  alpha: number
  trail: Array<{ x: number; y: number }>
}

type Theme = {
  mote: [number, number, number]
  link: [number, number, number]
  orb: [number, number, number]
}

const LOOP_LABELS = ['Reflect', 'Understand', 'Intend', 'Learn'] as const

const MAX_DPR = 2
const TRAIL_LENGTH = 14
const LINK_DISTANCE = 150

function readTheme(): Theme {
  const dark =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: dark)').matches

  return dark
    ? { mote: [192, 132, 252], link: [148, 120, 220], orb: [192, 132, 252] }
    : { mote: [170, 59, 255], link: [150, 90, 230], orb: [150, 70, 240] }
}

export function MemoryField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const prefersReduced = usePrefersReducedMotion()

  useEffect(() => {
    const canvasEl = canvasRef.current
    if (!canvasEl) return
    const context2d = canvasEl.getContext('2d')
    if (!context2d) return
    // Non-null aliases so nested render closures keep the narrowed types.
    const canvas = canvasEl
    const ctx = context2d

    let theme = readTheme()
    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
    let motes: Mote[] = []
    let rafId = 0
    let angle = 0

    // Pointer state, smoothed toward the target for gentle parallax.
    const pointer = { x: -9999, y: -9999, tx: -9999, ty: -9999, active: false }

    function moteCount() {
      // Scale particle count with area but keep it modest for smooth 60fps.
      return Math.round(Math.min(90, Math.max(36, (width * height) / 22000)))
    }

    function spawnMotes() {
      const count = moteCount()
      motes = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        radius: 0.8 + Math.random() * 2.2,
        alpha: 0.25 + Math.random() * 0.5,
        trail: [],
      }))
    }

    function resize() {
      width = window.innerWidth
      height = window.innerHeight
      dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      spawnMotes()
    }

    function drawLoop() {
      const cx = width / 2
      const cy = height / 2
      const orbitR = Math.min(width, height) * 0.22
      const [or, og, ob] = theme.orb

      // Breathing central orb (the companion).
      const breath = 1 + Math.sin(angle * 2) * 0.06
      const orbR = Math.min(width, height) * 0.05 * breath
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, orbR * 3)
      glow.addColorStop(0, `rgba(${or}, ${og}, ${ob}, 0.5)`)
      glow.addColorStop(0.4, `rgba(${or}, ${og}, ${ob}, 0.18)`)
      glow.addColorStop(1, `rgba(${or}, ${og}, ${ob}, 0)`)
      ctx.fillStyle = glow
      ctx.beginPath()
      ctx.arc(cx, cy, orbR * 3, 0, Math.PI * 2)
      ctx.fill()

      // Faint orbit ring.
      ctx.strokeStyle = `rgba(${or}, ${og}, ${ob}, 0.10)`
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(cx, cy, orbitR, 0, Math.PI * 2)
      ctx.stroke()

      // Four orbiting points of the loop.
      ctx.font =
        '600 13px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (let i = 0; i < LOOP_LABELS.length; i++) {
        const a = angle + (i / LOOP_LABELS.length) * Math.PI * 2
        const px = cx + Math.cos(a) * orbitR
        const py = cy + Math.sin(a) * orbitR
        const pulse = 0.55 + Math.sin(angle * 3 + i) * 0.2

        const pg = ctx.createRadialGradient(px, py, 0, px, py, 26)
        pg.addColorStop(0, `rgba(${or}, ${og}, ${ob}, ${0.6 * pulse})`)
        pg.addColorStop(1, `rgba(${or}, ${og}, ${ob}, 0)`)
        ctx.fillStyle = pg
        ctx.beginPath()
        ctx.arc(px, py, 26, 0, Math.PI * 2)
        ctx.fill()

        ctx.fillStyle = `rgba(${or}, ${og}, ${ob}, ${0.35 + pulse * 0.4})`
        ctx.fillText(LOOP_LABELS[i], px, py)
      }
    }

    function drawMotes(animated: boolean) {
      // Smooth the pointer toward its target for a gentle lean.
      pointer.x += (pointer.tx - pointer.x) * 0.06
      pointer.y += (pointer.ty - pointer.y) * 0.06

      // Connection lines (associations forming between memories).
      ctx.lineWidth = 1
      for (let i = 0; i < motes.length; i++) {
        for (let j = i + 1; j < motes.length; j++) {
          const dx = motes[i].x - motes[j].x
          const dy = motes[i].y - motes[j].y
          const dist = Math.hypot(dx, dy)
          if (dist < LINK_DISTANCE) {
            const a = (1 - dist / LINK_DISTANCE) * 0.16
            ctx.strokeStyle = `rgba(${theme.link[0]}, ${theme.link[1]}, ${theme.link[2]}, ${a})`
            ctx.beginPath()
            ctx.moveTo(motes[i].x, motes[i].y)
            ctx.lineTo(motes[j].x, motes[j].y)
            ctx.stroke()
          }
        }
      }

      ctx.globalCompositeOperation = 'lighter'
      const [mr, mg, mb] = theme.mote
      for (const mote of motes) {
        if (animated) {
          if (pointer.active) {
            const dx = pointer.x - mote.x
            const dy = pointer.y - mote.y
            const dist = Math.hypot(dx, dy)
            if (dist < 240 && dist > 0.001) {
              const pull = (1 - dist / 240) * 0.05
              mote.vx += (dx / dist) * pull
              mote.vy += (dy / dist) * pull
            }
          }

          mote.x += mote.vx
          mote.y += mote.vy
          mote.vx *= 0.99
          mote.vy *= 0.99

          // Wrap around the edges so the field feels boundless.
          if (mote.x < -20) mote.x = width + 20
          if (mote.x > width + 20) mote.x = -20
          if (mote.y < -20) mote.y = height + 20
          if (mote.y > height + 20) mote.y = -20

          mote.trail.push({ x: mote.x, y: mote.y })
          if (mote.trail.length > TRAIL_LENGTH) mote.trail.shift()
        }

        // Fading trail (memory persisting).
        for (let t = 0; t < mote.trail.length; t++) {
          const point = mote.trail[t]
          const fade = (t / mote.trail.length) * mote.alpha * 0.5
          ctx.fillStyle = `rgba(${mr}, ${mg}, ${mb}, ${fade})`
          ctx.beginPath()
          ctx.arc(point.x, point.y, mote.radius * (t / mote.trail.length), 0, Math.PI * 2)
          ctx.fill()
        }

        // The mote head with a soft glow.
        const g = ctx.createRadialGradient(
          mote.x,
          mote.y,
          0,
          mote.x,
          mote.y,
          mote.radius * 4,
        )
        g.addColorStop(0, `rgba(${mr}, ${mg}, ${mb}, ${mote.alpha})`)
        g.addColorStop(1, `rgba(${mr}, ${mg}, ${mb}, 0)`)
        ctx.fillStyle = g
        ctx.beginPath()
        ctx.arc(mote.x, mote.y, mote.radius * 4, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalCompositeOperation = 'source-over'
    }

    function render(animated: boolean) {
      ctx.clearRect(0, 0, width, height)
      drawLoop()
      drawMotes(animated)
    }

    function frame() {
      angle += 0.0016
      render(true)
      rafId = requestAnimationFrame(frame)
    }

    function start() {
      cancelAnimationFrame(rafId)
      if (prefersReduced) {
        // Seed a few trail points so the single static frame still has depth.
        for (const mote of motes) {
          mote.trail = Array.from({ length: 4 }, () => ({ x: mote.x, y: mote.y }))
        }
        render(false)
        return
      }
      rafId = requestAnimationFrame(frame)
    }

    function onPointerMove(event: PointerEvent) {
      pointer.tx = event.clientX
      pointer.ty = event.clientY
      if (!pointer.active) {
        pointer.x = event.clientX
        pointer.y = event.clientY
      }
      pointer.active = true
    }

    function onPointerLeave() {
      pointer.active = false
      pointer.tx = -9999
      pointer.ty = -9999
    }

    function onVisibility() {
      if (document.hidden) {
        cancelAnimationFrame(rafId)
      } else {
        start()
      }
    }

    const onColorScheme = () => {
      theme = readTheme()
    }
    const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)')

    resize()
    start()

    window.addEventListener('resize', resize)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerleave', onPointerLeave)
    document.addEventListener('visibilitychange', onVisibility)
    colorSchemeQuery.addEventListener('change', onColorScheme)

    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerleave', onPointerLeave)
      document.removeEventListener('visibilitychange', onVisibility)
      colorSchemeQuery.removeEventListener('change', onColorScheme)
    }
  }, [prefersReduced])

  return <canvas ref={canvasRef} className="memory-field" aria-hidden="true" />
}
