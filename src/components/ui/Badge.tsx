import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "primary" | "warm" | "success" | "new";
  className?: string;
}

export default function Badge({
  children,
  variant = "primary",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-block px-3 py-1 text-xs font-semibold rounded-button uppercase tracking-wider",
        variant === "primary" && "bg-primary text-white",
        variant === "warm" && "bg-warm text-secondary",
        variant === "success" && "bg-green-100 text-green-700",
        variant === "new" && "bg-warm-dark text-secondary",
        className
      )}
    >
      {children}
    </span>
  );
}
