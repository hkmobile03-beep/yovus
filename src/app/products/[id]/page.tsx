"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { getProductById, products } from "@/lib/products";
import { addToCart } from "@/lib/cart";
import ProductCard from "@/components/ProductCard";
import { useState } from "react";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const product = getProductById(id);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">商品不存在</h1>
        <Link href="/products" className="text-blue-600 hover:underline">
          返回商品列表
        </Link>
      </div>
    );
  }

  const discount = product.originalPrice
    ? Math.round((1 - product.price / product.originalPrice) * 100)
    : 0;

  const relatedProducts = products
    .filter((p) => p.category === product.category && p.id !== product.id)
    .slice(0, 4);

  const handleAddToCart = () => {
    addToCart(product, quantity);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-500 mb-8">
        <Link href="/" className="hover:text-gray-700">首页</Link>
        <span>/</span>
        <Link href="/products" className="hover:text-gray-700">全部商品</Link>
        <span>/</span>
        <Link href={`/products?category=${product.category}`} className="hover:text-gray-700">
          {product.category}
        </Link>
        <span>/</span>
        <span className="text-gray-900">{product.name}</span>
      </nav>

      {/* Product Detail */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
        {/* Image */}
        <div className="relative aspect-square bg-gray-100 rounded-2xl overflow-hidden">
          <img
            src={product.image}
            alt={product.name}
            className="w-full h-full object-cover"
          />
          {product.badge && (
            <span className="absolute top-4 left-4 bg-red-500 text-white text-sm px-3 py-1 rounded-full font-medium">
              {product.badge}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex flex-col">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
            {product.name}
          </h1>

          <div className="flex items-center gap-2 mb-4">
            <div className="flex text-amber-400">
              {"★".repeat(Math.floor(product.rating))}
              {"☆".repeat(5 - Math.floor(product.rating))}
            </div>
            <span className="text-sm text-gray-500">{product.rating} 分</span>
            <span className="text-sm text-gray-400">|</span>
            <span className="text-sm text-gray-500">{product.reviews} 条评价</span>
          </div>

          <div className="flex items-baseline gap-3 mb-6 pb-6 border-b border-gray-100">
            <span className="text-3xl font-bold text-red-500">&yen;{product.price}</span>
            {product.originalPrice && (
              <>
                <span className="text-lg text-gray-400 line-through">&yen;{product.originalPrice}</span>
                <span className="text-sm bg-red-50 text-red-500 px-2 py-0.5 rounded">省{discount}%</span>
              </>
            )}
          </div>

          <p className="text-gray-600 leading-relaxed mb-6">{product.description}</p>

          {product.features && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">产品特点</h3>
              <div className="flex flex-wrap gap-2">
                {product.features.map((feat) => (
                  <span
                    key={feat}
                    className="bg-gray-100 text-gray-700 text-sm px-3 py-1.5 rounded-lg"
                  >
                    {feat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quantity & Actions */}
          <div className="mt-auto pt-6 border-t border-gray-100">
            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm text-gray-700">数量</span>
              <div className="flex items-center border border-gray-200 rounded-lg">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-50 transition"
                >
                  -
                </button>
                <span className="px-4 py-2 text-sm font-medium min-w-[40px] text-center">
                  {quantity}
                </span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-50 transition"
                >
                  +
                </button>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleAddToCart}
                className={`flex-1 py-3 rounded-full font-medium transition-colors ${
                  added
                    ? "bg-green-500 text-white"
                    : "bg-black text-white hover:bg-gray-800"
                }`}
              >
                {added ? "已加入购物车 ✓" : "加入购物车"}
              </button>
              <Link
                href="/cart"
                onClick={() => addToCart(product, quantity)}
                className="flex-1 py-3 rounded-full font-medium text-center border-2 border-black text-black hover:bg-black hover:text-white transition-colors"
              >
                立即购买
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Related Products */}
      {relatedProducts.length > 0 && (
        <section className="mt-16">
          <h2 className="text-xl font-bold text-gray-900 mb-6">相关推荐</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
            {relatedProducts.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
