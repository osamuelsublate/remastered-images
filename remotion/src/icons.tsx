/**
 * Tiny built-in icon set for `icon` blocks — names must match
 * `ICON_NAMES` in `backend/app/prompts.py` (what the planner may pick).
 * Stroke-based 24x24 paths, drawn with the block's color.
 */

const PATHS: Record<string, React.ReactNode> = {
  arrow_right: <path d="M4 12h16m-6-6 6 6-6 6" />,
  arrow_up_right: <path d="M6 18 18 6M8 6h10v10" />,
  arrow_down: <path d="M12 4v16m-6-6 6 6 6-6" />,
  check: <path d="m4 12.5 5.5 5.5L20 6.5" />,
  x: <path d="M5 5l14 14M19 5 5 19" />,
  star: (
    <path d="m12 3 2.7 5.8 6.3.8-4.6 4.4 1.2 6.3L12 17.2 6.4 20.3l1.2-6.3L3 9.6l6.3-.8L12 3z" />
  ),
  bolt: <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />,
  circle: <circle cx="12" cy="12" r="9" />,
  quote: (
    <path d="M5 7c-1.5 1.2-2 2.8-2 5v5h6v-6H6c0-1.6.6-2.7 1.8-3.6L5 7zm10 0c-1.5 1.2-2 2.8-2 5v5h6v-6h-3c0-1.6.6-2.7 1.8-3.6L15 7z" />
  ),
  sparkles: (
    <path d="M12 3v4m0 10v4M3 12h4m10 0h4M6.3 6.3l2.1 2.1m7.2 7.2 2.1 2.1m0-11.4-2.1 2.1M8.4 15.6l-2.1 2.1" />
  ),
  plus: <path d="M12 4v16M4 12h16" />,
  play: <path d="M7 4.5v15l13-7.5-13-7.5z" />,
}

export const ICON_NAMES = Object.keys(PATHS)

export const BlockIcon: React.FC<{ name: string; color: string }> = ({ name, color }) => {
  const path = PATHS[name] ?? PATHS.sparkles
  const filled = name === 'play' || name === 'quote'
  return (
    <svg
      viewBox="0 0 24 24"
      width="100%"
      height="100%"
      fill={filled ? color : 'none'}
      stroke={filled ? 'none' : color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: 'block' }}
    >
      {path}
    </svg>
  )
}
