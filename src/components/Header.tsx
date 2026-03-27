"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCart, getCartCount } from "@/lib/cart";

export default function Header() {
  const [cartCount, setCartCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const update = () => setCartCount(getCartCount(getCart()));
    update();
    window.addEventListener("cart-updated", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("cart-updated", update);
      window.removeEventListener("storage", update);
    };
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-2xl font-bold tracking-tight text-gray-900">
            YOVUS
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            <Link href="/" className="text-sm font-medium text-gray-700 hover:text-black transition">
              首页
            </Link>
            <Link href="/products" className="text-sm font-medium text-gray-700 hover:text-black transition">
              全部商品
            </Link>
            <Link href="/products?category=电子产品" className="text-sm font-medium text-gray-700 hover:text-black transition">
              电子产品
            </Link>
            <Link href="/products?category=服饰" className="text-sm font-medium text-gray-700 hover:text-black transition">
              服饰
            </Link>
            <Link href="/products?category=家居" className="text-sm font-medium text-gray-700 hover:text-black transition">
              家居
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            <Link
              href="/cart"
              className="relative p-2 text-gray-700 hover:text-black transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 1 0-7.5 0v4.5m11.356-1.993 1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 0 1-1.12-1.243l1.264-12A1.125 1.125 0 0 1 5.513 7.5h12.974c.576 0 1.059.435 1.119 1.007ZM8.625 10.5a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm7.5 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
              </svg>
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-medium">
                  {cartCount}
                </span>
              )}
            </Link>

            <button
              className="md:hidden p-2 text-gray-700"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                <path strokeLinecap="round" strokeLinejoin="round" d={menuOpen ? "M6 18 18 6M6 6l12 12" : "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"} />
              </svg>
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav className="md:hidden pb-4 border-t border-gray-100 pt-4 flex flex-col gap-3">
            <Link href="/" className="text-sm font-medium text-gray-700" onClick={() => setMenuOpen(false)}>首页</Link>
            <Link href="/products" className="text-sm font-medium text-gray-700" onClick={() => setMenuOpen(false)}>全部商品</Link>
            <Link href="/products?category=电子产品" className="text-sm font-medium text-gray-700" onClick={() => setMenuOpen(false)}>电子产品</Link>
            <Link href="/products?category=服饰" className="text-sm font-medium text-gray-700" onClick={() => setMenuOpen(false)}>服饰</Link>
            <Link href="/products?category=家居" className="text-sm font-medium text-gray-700" onClick={() => setMenuOpen(false)}>家居</Link>
          </nav>
        )}
      </div>
    </header>
  );
}
