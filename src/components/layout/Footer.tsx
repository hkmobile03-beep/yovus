"use client";

import Link from "next/link";
import { Mail, Phone, Globe, MessageCircle, Heart } from "lucide-react";

const footerLinks = {
  products: [
    { href: "/products?category=mattress", label: "Mattresses" },
    { href: "/products?category=pillow", label: "Pillows" },
    { href: "/products?category=bedding", label: "Bedding" },
    { href: "/products?category=accessories", label: "Accessories" },
  ],
  support: [
    { href: "/about", label: "About Us" },
    { href: "/contact", label: "Contact" },
    { href: "#", label: "Shipping & Returns" },
    { href: "#", label: "FAQ" },
    { href: "#", label: "120-Day Trial" },
  ],
  company: [
    { href: "#", label: "Privacy Policy" },
    { href: "#", label: "Terms of Service" },
    { href: "#", label: "Warranty" },
    { href: "#", label: "Careers" },
  ],
};

export default function Footer() {
  return (
    <footer className="bg-secondary text-cream-light">
      {/* Newsletter Section */}
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <h3 className="text-xl font-bold text-white mb-1">
                Stay in touch
              </h3>
              <p className="text-cream/70 text-sm">
                Subscribe for exclusive offers and sleep tips.
              </p>
            </div>
            <form className="flex w-full md:w-auto gap-2" onSubmit={(e) => e.preventDefault()}>
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 md:w-72 px-5 py-3 rounded-button bg-white/10 border border-white/20 text-white placeholder-cream/50 focus:outline-none focus:border-primary text-sm"
              />
              <button
                type="submit"
                className="px-6 py-3 bg-primary text-white rounded-button font-medium hover:bg-primary-dark transition-colors text-sm"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Main Footer */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 bg-primary rounded-xl flex items-center justify-center text-white font-bold">
                Y
              </div>
              <span className="text-xl font-bold text-white">YOVUS</span>
            </Link>
            <p className="text-cream/60 text-sm leading-relaxed mb-4">
              Handcrafted sleep products designed for your comfort. Factory
              direct, no middlemen.
            </p>
            <div className="flex gap-3">
              <a href="#" className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary transition-colors" aria-label="Instagram">
                <Globe size={16} />
              </a>
              <a href="#" className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary transition-colors" aria-label="Facebook">
                <MessageCircle size={16} />
              </a>
              <a href="#" className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary transition-colors" aria-label="Twitter">
                <Heart size={16} />
              </a>
            </div>
          </div>

          {/* Products */}
          <div>
            <h4 className="text-white font-semibold mb-4">Products</h4>
            <ul className="space-y-2.5">
              {footerLinks.products.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-cream/60 hover:text-white text-sm transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="text-white font-semibold mb-4">Support</h4>
            <ul className="space-y-2.5">
              {footerLinks.support.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-cream/60 hover:text-white text-sm transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-white font-semibold mb-4">Company</h4>
            <ul className="space-y-2.5">
              {footerLinks.company.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-cream/60 hover:text-white text-sm transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
            <div className="mt-6 space-y-2 text-cream/60 text-sm">
              <div className="flex items-center gap-2">
                <Mail size={14} />
                <span>hello@yovus.com</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone size={14} />
                <span>0120-000-000</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-cream/40">
          <p>&copy; 2025 YOVUS. All rights reserved.</p>
          <div className="flex items-center gap-3">
            <span className="px-2 py-1 bg-white/10 rounded text-xs">VISA</span>
            <span className="px-2 py-1 bg-white/10 rounded text-xs">Mastercard</span>
            <span className="px-2 py-1 bg-white/10 rounded text-xs">AMEX</span>
            <span className="px-2 py-1 bg-white/10 rounded text-xs">PayPay</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
