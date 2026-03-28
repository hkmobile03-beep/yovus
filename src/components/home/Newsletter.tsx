"use client";

import ScrollReveal from "@/components/ui/ScrollReveal";

export default function Newsletter() {
  return (
    <section className="py-16 md:py-24 bg-gradient-to-br from-primary to-primary-dark text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Get ¥5,000 Off Your First Order
            </h2>
            <p className="text-white/80 mb-8">
              Subscribe to our newsletter and receive an exclusive discount
              code, plus sleep tips and early access to new products.
            </p>
            <form
              className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
              onSubmit={(e) => e.preventDefault()}
            >
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-5 py-3.5 rounded-button bg-white/15 border border-white/30 text-white placeholder-white/60 focus:outline-none focus:border-white text-sm"
              />
              <button
                type="submit"
                className="px-8 py-3.5 bg-white text-primary rounded-button font-semibold hover:bg-cream transition-colors text-sm whitespace-nowrap"
              >
                Get ¥5,000 Off
              </button>
            </form>
            <p className="text-xs text-white/50 mt-4">
              By subscribing, you agree to our Privacy Policy. Unsubscribe
              anytime.
            </p>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
