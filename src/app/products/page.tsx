"use client";

import { useState } from "react";
import { products, categories } from "@/data/products";
import ProductCard from "@/components/product/ProductCard";
import ScrollReveal from "@/components/ui/ScrollReveal";
import { cn } from "@/lib/utils";

export default function ProductsPage() {
  const [activeCategory, setActiveCategory] = useState("all");

  const filtered =
    activeCategory === "all"
      ? products
      : products.filter((p) => p.category === activeCategory);

  return (
    <>
      {/* Hero Banner */}
      <section className="bg-gradient-to-r from-section to-cream py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-3xl md:text-4xl font-bold text-secondary mb-3">
            Our Products
          </h1>
          <p className="text-secondary/60 max-w-xl mx-auto">
            Handcrafted sleep essentials designed with care. Every product comes
            with our 120-day risk-free trial.
          </p>
        </div>
      </section>

      {/* Filter & Grid */}
      <section className="py-12 md:py-16 bg-cream-light">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Category Tabs */}
          <div className="flex flex-wrap justify-center gap-2 mb-10">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={cn(
                  "px-5 py-2.5 rounded-button text-sm font-medium transition-all duration-200",
                  activeCategory === cat.id
                    ? "bg-primary text-white shadow-md"
                    : "bg-white text-secondary hover:bg-cream card-shadow"
                )}
              >
                {cat.name}
              </button>
            ))}
          </div>

          {/* Product Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filtered.map((product, index) => (
              <ScrollReveal key={product.id} delay={index * 80}>
                <ProductCard product={product} />
              </ScrollReveal>
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-16 text-secondary/50">
              No products found in this category.
            </div>
          )}
        </div>
      </section>
    </>
  );
}
