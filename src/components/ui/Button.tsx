"use client";

import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export default function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all duration-300 rounded-button",
        variant === "primary" &&
          "bg-primary text-white hover:bg-primary-dark shadow-md hover:shadow-lg",
        variant === "secondary" &&
          "bg-secondary text-white hover:bg-opacity-90",
        variant === "outline" &&
          "border-2 border-primary text-primary hover:bg-primary hover:text-white",
        variant === "ghost" &&
          "text-secondary hover:bg-cream",
        size === "sm" && "px-4 py-2 text-sm",
        size === "md" && "px-6 py-3 text-base",
        size === "lg" && "px-8 py-4 text-lg",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
