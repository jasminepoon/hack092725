import * as React from 'react';
import * as SwitchPrimitives from '@radix-ui/react-switch';
import { cn } from '@/lib/utils';

const Switch = React.forwardRef(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    ref={ref}
    className={cn(
      'relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60',
      'data-[state=unchecked]:bg-muted data-[state=unchecked]:border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary data-[state=checked]:shadow-[var(--shadow-sm)]',
      className,
    )}
    {...props}
  >
    <span
      aria-hidden
      className="absolute inset-0 rounded-full bg-gradient-to-br from-white/12 via-white/0 to-black/10"
    />
    <SwitchPrimitives.Thumb
      className={cn(
        'pointer-events-none relative z-10 block h-5 w-5 translate-x-0 rounded-full bg-card shadow-[var(--shadow-xs)] ring-0 transition-transform',
        'data-[state=checked]:translate-x-5',
      )}
    />
  </SwitchPrimitives.Root>
));
Switch.displayName = 'Switch';

export { Switch };
