import type {
  ReactNode,
  TextareaHTMLAttributes,
  InputHTMLAttributes,
} from 'react'
import { X } from './icons'

/* -------------------------------------------------------------------------- */
/* Atoms                                                                       */
/* -------------------------------------------------------------------------- */

const focusRing =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const buttonBase =
  'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 select-none disabled:opacity-40 disabled:pointer-events-none ' +
  focusRing

const buttonSizes: Record<'sm' | 'md', string> = {
  // md is the default; min-h-11 == 44px touch target.
  sm: 'min-h-10 px-3 text-sm',
  md: 'min-h-11 px-4 text-sm',
}

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-black hover:brightness-110 active:bg-primary-press shadow-[var(--shadow-sm)] focus-visible:ring-primary',
  secondary:
    'bg-surface-3 text-fg border border-line hover:bg-[#26262b] active:bg-surface-2 focus-visible:ring-primary',
  ghost:
    'text-fg-muted hover:bg-white/5 hover:text-fg focus-visible:ring-primary',
  danger:
    'text-error border border-error/40 hover:bg-error/10 active:bg-error/15 focus-visible:ring-error',
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  iconLeft,
  className = '',
  disabled,
  ...props
}: {
  children: ReactNode
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  loading?: boolean
  iconLeft?: ReactNode
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`${buttonBase} ${buttonSizes[size]} ${buttonVariants[variant]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Spinner /> : iconLeft}
      {children}
    </button>
  )
}

export function IconButton({
  children,
  label,
  variant = 'default',
  size = 'md',
  className = '',
  ...props
}: {
  children: ReactNode
  label: string
  variant?: 'default' | 'primary'
  size?: 'sm' | 'md'
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const sizeCls = size === 'sm' ? 'size-9' : 'size-11' // 36px / 44px
  const variants = {
    default:
      'border border-line text-fg-muted hover:bg-white/5 hover:text-fg focus-visible:ring-primary',
    primary:
      'bg-primary text-black hover:brightness-110 active:bg-primary-press focus-visible:ring-primary',
  }
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`grid shrink-0 place-items-center rounded-lg transition-colors duration-150 disabled:opacity-40 disabled:pointer-events-none ${sizeCls} ${variants[variant]} ${focusRing} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

const inputCls =
  'w-full min-h-11 rounded-lg border border-line bg-surface-2 px-3.5 py-2.5 text-sm text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/25 aria-[invalid=true]:border-error aria-[invalid=true]:focus:ring-error/25'

export function TextInput({
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${inputCls} ${className}`} {...props} />
}

export function TextArea({
  className = '',
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${inputCls} resize-none ${className}`} {...props} />
}

export function Field({
  label,
  hint,
  error,
  htmlFor,
  children,
}: {
  label: string
  hint?: string
  error?: string
  htmlFor?: string
  children: ReactNode
}) {
  const describedBy = error
    ? `${htmlFor}-error`
    : hint
      ? `${htmlFor}-hint`
      : undefined
  return (
    <div className="block">
      <div className="mb-1.5 flex items-baseline justify-between">
        <label htmlFor={htmlFor} className="text-sm font-medium text-fg-muted">
          {label}
        </label>
        {hint && !error && (
          <span id={describedBy} className="text-xs text-fg-subtle">
            {hint}
          </span>
        )}
      </div>
      {children}
      {error && (
        <p id={describedBy} className="mt-1.5 text-xs text-error">
          {error}
        </p>
      )}
    </div>
  )
}

export type BadgeTone =
  | 'default'
  | 'accent'
  | 'ok'
  | 'err'
  | 'run'
  | 'info'

export function Badge({
  children,
  tone = 'default',
}: {
  children: ReactNode
  tone?: BadgeTone
}) {
  const tones: Record<BadgeTone, string> = {
    default: 'bg-white/5 text-fg-muted border-white/10',
    accent: 'bg-primary/15 text-primary border-primary/30',
    ok: 'bg-success/15 text-success border-success/30',
    err: 'bg-error/15 text-error border-error/30',
    run: 'bg-warning/15 text-warning border-warning/30',
    info: 'bg-info/15 text-info border-info/30',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="carregando"
      className={`inline-block size-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  )
}

/* -------------------------------------------------------------------------- */
/* Molecules                                                                   */
/* -------------------------------------------------------------------------- */

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-white/5 ${className}`} />
}

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon: ReactNode
  title: string
  description: ReactNode
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-line bg-surface p-8 text-center">
      <div className="mb-3 grid size-12 place-items-center rounded-xl bg-white/5 text-fg-muted">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-fg">{title}</h3>
      <p className="mt-1 max-w-xs text-sm text-fg-subtle">{description}</p>
    </div>
  )
}

export function Alert({
  children,
  tone = 'error',
  onDismiss,
}: {
  children: ReactNode
  tone?: 'error' | 'info' | 'warning'
  onDismiss?: () => void
}) {
  const tones = {
    error: 'border-error/30 bg-error/10 text-error',
    info: 'border-info/30 bg-info/10 text-info',
    warning: 'border-warning/30 bg-warning/10 text-warning',
  }
  return (
    <div
      role="alert"
      className={`flex items-start justify-between gap-4 rounded-lg border px-4 py-2.5 text-sm ${tones[tone]}`}
    >
      <span className="min-w-0 [overflow-wrap:anywhere]">{children}</span>
      {onDismiss && (
        <IconButton
          label="Fechar aviso"
          size="sm"
          onClick={onDismiss}
          className="-mr-1.5 -my-1 border-transparent text-current hover:bg-white/10"
        >
          <X size={16} />
        </IconButton>
      )}
    </div>
  )
}

export function ProgressBar({
  label,
  percent,
}: {
  label: string
  percent: number
}) {
  return (
    <div className="border-b border-line px-4 py-2.5">
      <div className="mb-1 flex justify-between text-xs text-fg-muted">
        <span>{label}</span>
        <span>{percent}%</span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
