"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getProductBySlug, getRelatedProducts } from "@/data/products";
import { formatPrice, cn } from "@/lib/utils";
import { useCart } from "@/context/CartContext";
import ProductCard from "@/components/product/ProductCard";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import ScrollReveal from "@/components/ui/ScrollReveal";
import {
  Star,
  Minus,
  Plus,
  ShoppingBag,
  Truck,
  Shield,
  Clock,
  Check,
} from "lucide-react";

export default function ProductDetailPage() {
  const { slug } = useParams();
  const product = getProductBySlug(slug as string);
  const { addItem } = useCart();
  const [selectedSize, setSelectedSize] = useState(
    product?.sizes?.[0]?.name ?? ""
  );
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  if (!product) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-secondary mb-4">
            Product Not Found
          </h1>
          <Link href="/products">
            <Button>Back to Products</Button>
          </Link>
        </div>
      </div>
    );
  }

  const currentPrice =
    product.sizes?.find((s) => s.name === selectedSize)?.price ??
    product.price;

  const related = getRelatedProducts(product.id);

  const handleAddToCart = () => {
    for (let i = 0; i < quantity; i++) {
      addItem(product, selectedSize || undefined);
    }
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  return (
    <>
      {/* Breadcrumb */}
      <div className="bg-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <nav className="flex items-center gap-2 text-sm text-secondary/50">
            <Link href="/" className="hover:text-primary">
              Home
            </Link>
            <span>/</span>
            <Link href="/products" className="hover:text-primary">
              Products
            </Link>
            <span>/</span>
            <span className="text-secondary">{product.name}</span>
          </nav>
        </div>
      </div>

      {/* Product Detail */}
      <section className="py-8 md:py-12 bg-cream-light">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
            {/* Image Gallery */}
            <ScrollReveal>
              <div className="space-y-4">
                <div className="bg-white rounded-card overflow-hidden card-shadow aspect-square flex items-center justify-center relative">
                  {product.badge && (
                    <div className="absolute top-4 left-4 z-10">
                      <Badge
                        variant={
                          product.badge === "NEW" ? "new" : "primary"
                        }
                      >
                        {product.badge}
                      </Badge>
                    </div>
                  )}
                  <div className="text-center">
                    <div className="w-40 h-40 mx-auto mb-4 bg-gradient-to-br from-primary/10 to-warm/50 rounded-3xl flex items-center justify-center">
                      <span className="text-7xl">
                        {product.category === "mattress"
                          ? "🛏️"
                          : product.category === "pillow"
                          ? "😴"
                          : product.category === "bedding"
                          ? "🛋️"
                          : "✨"}
                      </span>
                    </div>
                    <p className="text-secondary/40 text-sm">
                      {product.nameJa}
                    </p>
                  </div>
                </div>
                {/* Thumbnail row */}
                <div className="grid grid-cols-4 gap-3">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={cn(
                        "aspect-square rounded-soft bg-white card-shadow flex items-center justify-center cursor-pointer",
                        i === 0 && "ring-2 ring-primary"
                      )}
                    >
                      <span className="text-2xl opacity-60">
                        {product.category === "mattress"
                          ? "🛏️"
                          : product.category === "pillow"
                          ? "😴"
                          : product.category === "bedding"
                          ? "🛋️"
                          : "✨"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>

            {/* Product Info */}
            <ScrollReveal delay={100}>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-secondary mb-2">
                  {product.name}
                </h1>
                <p className="text-secondary/50 mb-3">{product.nameJa}</p>

                {/* Rating */}
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        size={16}
                        className={
                          i < Math.floor(product.rating)
                            ? "fill-yellow-400 text-yellow-400"
                            : "text-gray-200"
                        }
                      />
                    ))}
                  </div>
                  <span className="text-sm text-secondary/60">
                    {product.rating} ({product.reviewCount.toLocaleString()}{" "}
                    reviews)
                  </span>
                </div>

                {/* Price */}
                <div className="mb-6">
                  <span className="text-3xl font-bold text-secondary">
                    {formatPrice(currentPrice)}
                  </span>
                  <span className="text-sm text-secondary/50 ml-2">
                    (tax included)
                  </span>
                </div>

                {/* Size Selector */}
                {product.sizes && product.sizes.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-sm font-semibold text-secondary mb-3">
                      Size
                    </h3>
                    <div className="grid grid-cols-2 gap-2">
                      {product.sizes.map((size) => (
                        <button
                          key={size.name}
                          onClick={() => setSelectedSize(size.name)}
                          className={cn(
                            "p-3 rounded-soft text-left transition-all duration-200 border-2",
                            selectedSize === size.name
                              ? "border-primary bg-primary/5"
                              : "border-cream hover:border-primary/30 bg-white"
                          )}
                        >
                          <div className="font-medium text-sm text-secondary">
                            {size.name}
                          </div>
                          <div className="text-xs text-secondary/50">
                            {size.dimensions}
                          </div>
                          <div className="text-sm font-semibold text-primary mt-1">
                            {formatPrice(size.price)}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Quantity */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-secondary mb-3">
                    Quantity
                  </h3>
                  <div className="inline-flex items-center border-2 border-cream rounded-soft">
                    <button
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                      className="w-10 h-10 flex items-center justify-center text-secondary hover:bg-cream transition-colors"
                    >
                      <Minus size={16} />
                    </button>
                    <span className="w-12 text-center font-medium text-secondary">
                      {quantity}
                    </span>
                    <button
                      onClick={() => setQuantity(quantity + 1)}
                      className="w-10 h-10 flex items-center justify-center text-secondary hover:bg-cream transition-colors"
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                </div>

                {/* Add to Cart */}
                <button
                  onClick={handleAddToCart}
                  className={cn(
                    "w-full py-4 rounded-button font-semibold text-lg flex items-center justify-center gap-2 transition-all duration-300",
                    added
                      ? "bg-green-500 text-white"
                      : "bg-primary text-white hover:bg-primary-dark shadow-lg hover:shadow-xl"
                  )}
                >
                  {added ? (
                    <>
                      <Check size={20} /> Added to Cart!
                    </>
                  ) : (
                    <>
                      <ShoppingBag size={20} /> Add to Cart —{" "}
                      {formatPrice(currentPrice * quantity)}
                    </>
                  )}
                </button>

                {/* Trust badges */}
                <div className="grid grid-cols-3 gap-3 mt-6">
                  <div className="flex items-center gap-2 text-xs text-secondary/60">
                    <Clock size={14} className="text-primary" />
                    120-Day Trial
                  </div>
                  <div className="flex items-center gap-2 text-xs text-secondary/60">
                    <Truck size={14} className="text-primary" />
                    Free Shipping
                  </div>
                  <div className="flex items-center gap-2 text-xs text-secondary/60">
                    <Shield size={14} className="text-primary" />
                    10-Year Warranty
                  </div>
                </div>

                {/* Description */}
                <div className="mt-8 pt-6 border-t border-cream">
                  <p className="text-secondary/70 leading-relaxed">
                    {product.description}
                  </p>
                </div>

                {/* Features Accordion */}
                <div className="mt-6 space-y-2">
                  {product.features.map((feature, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 text-sm text-secondary/70"
                    >
                      <Check
                        size={16}
                        className="text-primary mt-0.5 flex-shrink-0"
                      />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Related Products */}
      {related.length > 0 && (
        <section className="py-12 md:py-16 bg-section">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-secondary mb-8">
              You May Also Like
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {related.map((p, index) => (
                <ScrollReveal key={p.id} delay={index * 100}>
                  <ProductCard product={p} />
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
