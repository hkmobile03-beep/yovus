"use client";

import Link from "next/link";
import { Product } from "@/data/products";
import { formatPrice } from "@/lib/utils";
import Badge from "@/components/ui/Badge";
import { Star, ShoppingBag } from "lucide-react";
import { useCart } from "@/context/CartContext";

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const { addItem } = useCart();

  return (
    <div className="group bg-white rounded-card overflow-hidden card-shadow hover:card-shadow-hover transition-all duration-300">
      {/* Image */}
      <Link href={`/products/${product.slug}`}>
        <div className="relative aspect-square bg-section overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center product-image-zoom">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-3 bg-gradient-to-br from-primary/10 to-warm/50 rounded-2xl flex items-center justify-center">
                <span className="text-4xl">
                  {product.category === "mattress"
                    ? "🛏️"
                    : product.category === "pillow"
                    ? "😴"
                    : product.category === "bedding"
                    ? "🛋️"
                    : "✨"}
                </span>
              </div>
              <p className="text-xs text-secondary/40">{product.nameJa}</p>
            </div>
          </div>
          {product.badge && (
            <div className="absolute top-3 left-3 z-10">
              <Badge variant={product.badge === "NEW" ? "new" : "primary"}>
                {product.badge}
              </Badge>
            </div>
          )}
        </div>
      </Link>

      {/* Content */}
      <div className="p-4">
        <Link href={`/products/${product.slug}`}>
          <h3 className="font-semibold text-secondary text-sm mb-1 group-hover:text-primary transition-colors">
            {product.name}
          </h3>
        </Link>

        {/* Rating */}
        <div className="flex items-center gap-1 mb-2">
          <div className="flex">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                size={12}
                className={
                  i < Math.floor(product.rating)
                    ? "fill-yellow-400 text-yellow-400"
                    : "text-gray-200"
                }
              />
            ))}
          </div>
          <span className="text-xs text-secondary/50">
            ({product.reviewCount.toLocaleString()})
          </span>
        </div>

        {/* Price & Cart */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-lg font-bold text-secondary">
              {formatPrice(product.price)}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-secondary/40 line-through ml-2">
                {formatPrice(product.originalPrice)}
              </span>
            )}
          </div>
          <button
            onClick={() =>
              addItem(product, product.sizes?.[0]?.name)
            }
            className="w-9 h-9 rounded-full bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all duration-200 flex items-center justify-center"
            aria-label="Add to cart"
          >
            <ShoppingBag size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
