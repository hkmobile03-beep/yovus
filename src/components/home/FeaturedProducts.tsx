"use client";

import Link from "next/link";
import { products } from "@/data/products";
import ProductCard from "@/components/product/ProductCard";
import ScrollReveal from "@/components/ui/ScrollReveal";
import Button from "@/components/ui/Button";

export default function FeaturedProducts() {
  const featured = products.slice(0, 4);

  return (
    <section className="py-16 md:py-24 bg-cream-light">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="text-center mb-12">
            <span className="text-primary text-sm font-medium uppercase tracking-wider">
              Our Collection
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-secondary mt-2 mb-4">
              Featured Products
            </h2>
            <p className="text-secondary/60 max-w-2xl mx-auto">
              Handcrafted sleep essentials designed to bring comfort and
              softness to your daily life. Factory direct, no middlemen.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {featured.map((product, index) => (
            <ScrollReveal key={product.id} delay={index * 100}>
              <ProductCard product={product} />
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal>
          <div className="text-center mt-10">
            <Link href="/products">
              <Button variant="outline">View All Products</Button>
            </Link>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
