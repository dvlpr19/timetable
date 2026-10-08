import logo from '@/assets/logo.png';
import { cn } from '@/lib/cn';

const SIZES = {
  sm: 'h-12 w-12',
  md: 'h-16 w-16',
  lg: 'h-24 w-24',
  xl: 'h-32 w-32',
};

/** Academy logo on a white disc, so it stays readable on the blue sidebar and header too. */
export function BrandMark({
  size = 'md',
  className = '',
}: {
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <img
      src={logo}
      alt=""
      aria-hidden="true"
      className={cn(
        'shrink-0 rounded-full bg-white object-contain p-1 shadow-soft',
        SIZES[size],
        className,
      )}
    />
  );
}
