"use client";

import { useState } from "react";
import Link from "next/link";
import { ShoppingBag, Menu, X } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/products", label: "Products", labelJa: "商品一覧" },
  { href: "/about", label: "About", labelJa: "ブランドについて" },
  { href: "/contact", label: "Contact", labelJa: "お問い合わせ" },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { totalItems } = useCart();

  return (
    <>
      {/* Announcement Bar */}
      <div className="bg-primary text-white text-center py-2.5 px-4 text-sm font-medium">
        <span className="hidden sm:inline">
          120-Day Free Trial | Free Shipping | 10-Year Warranty |
          Interest-Free 3 Installments
        </span>
        <span className="sm:hidden">
          120-Day Free Trial | Free Shipping
        </span>
      </div>

      {/* Main Nav */}
      <nav className="sticky top-0 z-50 bg-cream-light/95 backdrop-blur-md border-b border-cream">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 lg:h-20">
            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 rounded-soft text-secondary hover:bg-cream"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={24} /> : <Menu size={24} />}
            </button>

            {/* Logo */}
            <Link
              href="/"
              className="flex items-center gap-2 text-2xl font-bold text-secondary"
            >
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-white text-lg font-bold">
                Y
              </div>
              <span>YOVUS</span>
            </Link>

            {/* Desktop Nav Links */}
            <div className="hidden lg:flex items-center gap-8">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-secondary hover:text-primary transition-colors duration-200 font-medium"
                >
                  {link.label}
                </Link>
              ))}
            </div>

            {/* Cart */}
            <Link
              href="/cart"
              className="relative p-2 rounded-soft text-secondary hover:bg-cream transition-colors"
            >
              <ShoppingBag size={24} />
              {totalItems > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary text-white text-xs font-bold rounded-full flex items-center justify-center animate-cart-bounce">
                  {totalItems}
                </span>
              )}
            </Link>
          </div>
        </div>

        {/* Mobile Menu */}
        <div
          className={cn(
            "lg:hidden overflow-hidden transition-all duration-300",
            mobileOpen ? "max-h-64 border-t border-cream" : "max-h-0"
          )}
        >
          <div className="px-4 py-4 space-y-3 bg-cream-light">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block py-2 px-4 text-secondary hover:text-primary hover:bg-cream rounded-soft transition-colors font-medium"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>
    </>
  );
}
