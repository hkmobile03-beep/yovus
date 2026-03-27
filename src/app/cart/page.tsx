"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CartItem, getCart, removeFromCart, updateQuantity, getCartTotal } from "@/lib/cart";

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>([]);

  const refresh = () => setItems(getCart());

  useEffect(() => {
    refresh();
    window.addEventListener("cart-updated", refresh);
    return () => window.removeEventListener("cart-updated", refresh);
  }, []);

  const total = getCartTotal(items);

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="text-6xl mb-4">🛒</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">购物车是空的</h1>
        <p className="text-gray-500 mb-6">快去挑选心仪的商品吧</p>
        <Link
          href="/products"
          className="inline-block bg-black text-white px-8 py-3 rounded-full font-medium hover:bg-gray-800 transition"
        >
          去选购
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">
        购物车 <span className="text-gray-400 text-lg font-normal">({items.length} 件商品)</span>
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => (
            <div
              key={item.product.id}
              className="bg-white rounded-xl p-4 flex gap-4 border border-gray-100"
            >
              <Link href={`/products/${item.product.id}`} className="shrink-0">
                <img
                  src={item.product.image}
                  alt={item.product.name}
                  className="w-24 h-24 object-cover rounded-lg"
                />
              </Link>
              <div className="flex-1 min-w-0">
                <Link href={`/products/${item.product.id}`}>
                  <h3 className="font-medium text-gray-900 truncate hover:text-blue-600 transition">
                    {item.product.name}
                  </h3>
                </Link>
                <p className="text-sm text-gray-500 mt-1">{item.product.category}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-lg font-bold text-red-500">
                    &yen;{item.product.price}
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center border border-gray-200 rounded-lg">
                      <button
                        onClick={() => {
                          if (item.quantity <= 1) {
                            removeFromCart(item.product.id);
                          } else {
                            updateQuantity(item.product.id, item.quantity - 1);
                          }
                          refresh();
                        }}
                        className="px-2.5 py-1 text-gray-600 hover:bg-gray-50"
                      >
                        -
                      </button>
                      <span className="px-3 py-1 text-sm font-medium">{item.quantity}</span>
                      <button
                        onClick={() => {
                          updateQuantity(item.product.id, item.quantity + 1);
                          refresh();
                        }}
                        className="px-2.5 py-1 text-gray-600 hover:bg-gray-50"
                      >
                        +
                      </button>
                    </div>
                    <button
                      onClick={() => {
                        removeFromCart(item.product.id);
                        refresh();
                      }}
                      className="p-1.5 text-gray-400 hover:text-red-500 transition"
                      title="删除"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 h-fit sticky top-24">
          <h2 className="font-bold text-gray-900 mb-4">订单摘要</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between text-gray-600">
              <span>商品小计</span>
              <span>&yen;{total.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>运费</span>
              <span className="text-green-600">{total >= 99 ? "免运费" : "¥10.00"}</span>
            </div>
            <div className="border-t border-gray-100 pt-3 flex justify-between font-bold text-lg text-gray-900">
              <span>合计</span>
              <span className="text-red-500">
                &yen;{(total < 99 ? total + 10 : total).toFixed(2)}
              </span>
            </div>
          </div>
          <Link
            href="/checkout"
            className="block w-full bg-black text-white text-center py-3 rounded-full font-medium mt-6 hover:bg-gray-800 transition"
          >
            去结算
          </Link>
          <Link
            href="/products"
            className="block text-center text-sm text-gray-500 mt-3 hover:text-gray-700 transition"
          >
            继续选购
          </Link>
        </div>
      </div>
    </div>
  );
}
