"use client";

import Link from "next/link";
import Button from "@/components/ui/Button";
import ScrollReveal from "@/components/ui/ScrollReveal";

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-cream-light via-warm-light to-cream">
      {/* Decorative blobs */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-warm/30 rounded-full blur-3xl" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Text Content */}
          <ScrollReveal>
            <div className="max-w-xl">
              <span className="inline-block px-4 py-2 bg-primary/10 text-primary rounded-button text-sm font-medium mb-6">
                120-Day Free Trial
              </span>
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-secondary leading-tight mb-6">
                Sleep Better,
                <br />
                <span className="gradient-text">Live Softer</span>
              </h1>
              <p className="text-lg text-secondary/70 leading-relaxed mb-8">
                Handcrafted hybrid mattresses combining premium urethane foam
                with independent coil springs. Designed for your body, delivered
                from our factory to your door.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link href="/products">
                  <Button size="lg">Shop Now</Button>
                </Link>
                <Link href="/about">
                  <Button variant="outline" size="lg">
                    Our Story
                  </Button>
                </Link>
              </div>

              {/* Mini stats */}
              <div className="flex gap-8 mt-10 pt-8 border-t border-secondary/10">
                <div>
                  <div className="text-2xl font-bold text-secondary">98%</div>
                  <div className="text-sm text-secondary/60">
                    Satisfaction Rate
                  </div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-secondary">
                    130K+
                  </div>
                  <div className="text-sm text-secondary/60">Units Sold</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-secondary">10yr</div>
                  <div className="text-sm text-secondary/60">Warranty</div>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Product Image Placeholder */}
          <ScrollReveal delay={200}>
            <div className="relative">
              <div className="relative bg-white rounded-3xl overflow-hidden card-shadow aspect-square flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-32 h-32 mx-auto mb-6 bg-gradient-to-br from-primary/20 to-warm rounded-3xl flex items-center justify-center animate-float">
                    <span className="text-6xl">🛏️</span>
                  </div>
                  <h3 className="text-xl font-bold text-secondary mb-2">
                    YOVUS Mattress
                  </h3>
                  <p className="text-secondary/60 text-sm">
                    Hybrid Design | Made with Care
                  </p>
                  <div className="mt-4 text-2xl font-bold text-primary">
                    From ¥79,800
                  </div>
                </div>
              </div>
              {/* Floating badge */}
              <div className="absolute -top-4 -right-4 bg-warm text-secondary px-4 py-2 rounded-card font-semibold text-sm card-shadow rotate-3">
                Free Shipping
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}
