/*
 * Single icon set — 24x24 line icons, 1.5 stroke, currentColor.
 * Replaces the ad-hoc text glyphs (◫ + ↑ ✓ ✕ ▶ ❚❚) with one consistent
 * style (Rams: minucioso/estilo único; Krug: affordance clara).
 */
import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

function Svg({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  )
}

export function Plus(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  )
}

export function ArrowUp(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </Svg>
  )
}

export function Play(props: IconProps) {
  return (
    <Svg fill="currentColor" stroke="none" {...props}>
      <path d="M8 5.5v13a1 1 0 0 0 1.52.85l10.5-6.5a1 1 0 0 0 0-1.7L9.52 4.65A1 1 0 0 0 8 5.5Z" />
    </Svg>
  )
}

export function Pause(props: IconProps) {
  return (
    <Svg fill="currentColor" stroke="none" {...props}>
      <path d="M7 4h3v16H7zM14 4h3v16h-3z" />
    </Svg>
  )
}

export function Check(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 12.5l4.5 4.5L19 6.5" />
    </Svg>
  )
}

export function X(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Svg>
  )
}

export function Download(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4v11M8 11l4 4 4-4M5 19h14" />
    </Svg>
  )
}

export function Video(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M22 8l-6 4 6 4V8Z" />
      <rect x="2" y="6" width="14" height="12" rx="2" />
    </Svg>
  )
}

export function Sparkles(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3Z" />
      <path d="M19 14l.8 1.9L22 17l-2.2.9L19 20l-.8-2.1L16 17l2.2-1.1L19 14Z" />
    </Svg>
  )
}

export function Refresh(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v5h-5" />
    </Svg>
  )
}

export function Images(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="9" cy="9" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </Svg>
  )
}

export function AlertTriangle(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5l9 16H3l9-16Z" />
      <path d="M12 10v4M12 17.5h.01" />
    </Svg>
  )
}

export function Mic(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </Svg>
  )
}

export function Square(props: IconProps) {
  return (
    <Svg fill="currentColor" stroke="none" {...props}>
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </Svg>
  )
}

export function Trash(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6.5 7l.8 12a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.8-12" />
      <path d="M10 11v6M14 11v6" />
    </Svg>
  )
}

export function Type(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 6V4h14v2M12 4v16M9 20h6" />
    </Svg>
  )
}

export function Shapes(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="13" width="8" height="8" rx="1" />
      <circle cx="16.5" cy="16.5" r="4.5" />
      <path d="M12 3l4.5 7h-9L12 3Z" />
    </Svg>
  )
}

export function Pencil(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 20l4.2-.5L20 7.7a2 2 0 0 0 0-2.8l-1.9-1.9a2 2 0 0 0-2.8 0L3.5 14.8 3 19a1 1 0 0 0 1 1Z" />
      <path d="M14.5 4.5l4 4" />
    </Svg>
  )
}
