import { APP_ICONS } from '../lib/brand'

type AppLogoProps = {
  size?: number
  className?: string
}

export function AppLogo({ size = 32, className }: AppLogoProps) {
  const src = size >= 64 ? APP_ICONS.lg : size >= 40 ? APP_ICONS.md : APP_ICONS.sm

  return (
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      className={className ? `app-logo ${className}` : 'app-logo'}
      aria-hidden="true"
    />
  )
}
