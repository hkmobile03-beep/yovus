"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CartItem, getCart, getCartTotal, saveCart } from "@/lib/cart";

export default function CheckoutPage() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setItems(getCart());
  }, []);

  const total = getCartTotal(items);
  const shipping = total >= 99 ? 0 : 10;

  if (submitted) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="text-6xl mb-4">🎉</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">订单提交成功！</h1>
        <p className="text-gray-500 mb-6">感谢您的购买，我们将尽快为您发货</p>
        <Link
          href="/"
          className="inline-block bg-black text-white px-8 py-3 rounded-full font-medium hover:bg-gray-800 transition"
        >
          返回首页
        </Link>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">购物车为空</h1>
        <Link href="/products" className="text-blue-600 hover:underline">
          去选购商品
        </Link>
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    saveCart([]);
    setSubmitted(true);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">结算</h1>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Shipping Info */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h2 className="font-bold text-gray-900 mb-4">收货信息</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-700 mb-1">收货人</label>
                  <input
                    required
                    type="text"
                    placeholder="请输入姓名"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-700 mb-1">手机号</label>
                  <input
                    required
                    type="tel"
                    placeholder="请输入手机号"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm text-gray-700 mb-1">详细地址</label>
                  <input
                    required
                    type="text"
                    placeholder="省/市/区/街道/门牌号"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
              </div>
            </div>

            {/* Payment */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h2 className="font-bold text-gray-900 mb-4">支付方式</h2>
              <div className="space-y-3">
                {["微信支付", "支付宝", "银行卡支付"].map((method, i) => (
                  <label
                    key={method}
                    className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition"
                  >
                    <input
                      type="radio"
                      name="payment"
                      defaultChecked={i === 0}
                      className="accent-black"
                    />
                    <span className="text-sm text-gray-700">{method}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Order Summary */}
          <div className="bg-white rounded-xl p-6 border border-gray-100 h-fit sticky top-24">
            <h2 className="font-bold text-gray-900 mb-4">订单详情</h2>
            <div className="space-y-3 mb-4">
              {items.map((item) => (
                <div key={item.product.id} className="flex items-center gap-3">
                  <img
                    src={item.product.image}
                    alt={item.product.name}
                    className="w-12 h-12 object-cover rounded-lg"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.product.name}
                    </p>
                    <p className="text-xs text-gray-500">x{item.quantity}</p>
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    &yen;{(item.product.price * item.quantity).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
            <div className="border-t border-gray-100 pt-3 space-y-2 text-sm">
              <div className="flex justify-between text-gray-600">
                <span>商品小计</span>
                <span>&yen;{total.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>运费</span>
                <span className={shipping === 0 ? "text-green-600" : ""}>
                  {shipping === 0 ? "免运费" : `¥${shipping.toFixed(2)}`}
                </span>
              </div>
              <div className="border-t border-gray-100 pt-2 flex justify-between font-bold text-lg text-gray-900">
                <span>应付总额</span>
                <span className="text-red-500">&yen;{(total + shipping).toFixed(2)}</span>
              </div>
            </div>
            <button
              type="submit"
              className="w-full bg-black text-white py-3 rounded-full font-medium mt-6 hover:bg-gray-800 transition"
            >
              提交订单
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
