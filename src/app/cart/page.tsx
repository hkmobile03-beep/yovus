"use client";

import Link from "next/link";
import { useCart } from "@/context/CartContext";
import { formatPrice } from "@/lib/utils";
import Button from "@/components/ui/Button";
import { Minus, Plus, X, ShoppingBag, ArrowLeft } from "lucide-react";

export default function CartPage() {
  const { items, removeItem, updateQuantity, totalPrice, clearCart } =
    useCart();

  if (items.length === 0) {
    return (
      <section className="py-20 md:py-32 bg-cream-light">
        <div className="max-w-md mx-auto px-4 text-center">
          <div className="w-24 h-24 mx-auto mb-6 bg-section rounded-full flex items-center justify-center">
            <ShoppingBag className="text-secondary/30" size={40} />
          </div>
          <h1 className="text-2xl font-bold text-secondary mb-3">
            Your Cart is Empty
          </h1>
          <p className="text-secondary/60 mb-8">
            Looks like you haven&apos;t added any items yet. Browse our
            collection to find your perfect sleep solution.
          </p>
          <Link href="/products">
            <Button size="lg">Browse Products</Button>
          </Link>
        </div>
      </section>
    );
  }

  const shippingCost = 0;
  const grandTotal = totalPrice + shippingCost;

  return (
    <>
      <section className="bg-gradient-to-r from-section to-cream py-8 md:py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl md:text-3xl font-bold text-secondary">
            Shopping Cart
          </h1>
          <p className="text-secondary/60 mt-1">
            {items.length} item{items.length > 1 ? "s" : ""} in your cart
          </p>
        </div>
      </section>

      <section className="py-8 md:py-12 bg-cream-light">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Cart Items */}
            <div className="lg:col-span-2 space-y-4">
              {items.map((item) => (
                <div
                  key={`${item.product.id}-${item.selectedSize || ""}`}
                  className="bg-white rounded-card p-4 md:p-6 card-shadow flex gap-4"
                >
                  {/* Image */}
                  <div className="w-24 h-24 md:w-32 md:h-32 bg-section rounded-soft flex-shrink-0 flex items-center justify-center">
                    <span className="text-3xl md:text-4xl">
                      {item.product.category === "mattress"
                        ? "🛏️"
                        : item.product.category === "pillow"
                        ? "😴"
                        : item.product.category === "bedding"
                        ? "🛋️"
                        : "✨"}
                    </span>
                  </div>

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div>
                        <Link
                          href={`/products/${item.product.slug}`}
                          className="font-semibold text-secondary hover:text-primary transition-colors"
                        >
                          {item.product.name}
                        </Link>
                        {item.selectedSize && (
                          <p className="text-sm text-secondary/50 mt-0.5">
                            Size: {item.selectedSize}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() =>
                          removeItem(
                            item.product.id,
                            item.selectedSize
                          )
                        }
                        className="p-1 text-secondary/30 hover:text-red-500 transition-colors"
                        aria-label="Remove item"
                      >
                        <X size={18} />
                      </button>
                    </div>

                    <div className="flex items-end justify-between mt-4">
                      <div className="inline-flex items-center border border-cream rounded-soft">
                        <button
                          onClick={() =>
                            updateQuantity(
                              item.product.id,
                              item.quantity - 1,
                              item.selectedSize
                            )
                          }
                          className="w-8 h-8 flex items-center justify-center text-secondary/50 hover:bg-cream transition-colors"
                        >
                          <Minus size={14} />
                        </button>
                        <span className="w-10 text-center text-sm font-medium">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() =>
                            updateQuantity(
                              item.product.id,
                              item.quantity + 1,
                              item.selectedSize
                            )
                          }
                          className="w-8 h-8 flex items-center justify-center text-secondary/50 hover:bg-cream transition-colors"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      <span className="font-bold text-secondary">
                        {formatPrice(item.unitPrice * item.quantity)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              <div className="flex justify-between items-center pt-2">
                <Link
                  href="/products"
                  className="flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <ArrowLeft size={14} /> Continue Shopping
                </Link>
                <button
                  onClick={clearCart}
                  className="text-sm text-secondary/40 hover:text-red-500 transition-colors"
                >
                  Clear Cart
                </button>
              </div>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-card p-6 card-shadow sticky top-24">
                <h2 className="text-lg font-bold text-secondary mb-4">
                  Order Summary
                </h2>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between text-secondary/70">
                    <span>Subtotal</span>
                    <span>{formatPrice(totalPrice)}</span>
                  </div>
                  <div className="flex justify-between text-secondary/70">
                    <span>Shipping</span>
                    <span className="text-green-600 font-medium">Free</span>
                  </div>
                  <div className="border-t border-cream pt-3 flex justify-between text-lg font-bold text-secondary">
                    <span>Total</span>
                    <span>{formatPrice(grandTotal)}</span>
                  </div>
                </div>

                <div className="mt-3 text-xs text-secondary/50">
                  Or 3 interest-free payments of{" "}
                  {formatPrice(Math.ceil(grandTotal / 3))}
                </div>

                <button className="w-full mt-6 py-4 bg-primary text-white rounded-button font-semibold hover:bg-primary-dark transition-colors shadow-lg">
                  Proceed to Checkout
                </button>

                <div className="mt-4 text-center text-xs text-secondary/40 space-y-1">
                  <p>120-Day Free Trial on all products</p>
                  <p>Secure checkout with SSL encryption</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
