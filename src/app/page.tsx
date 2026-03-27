import Link from "next/link";
import ProductCard from "@/components/ProductCard";
import { products } from "@/lib/products";

const featuredProducts = products.filter((p) => p.badge).slice(0, 4);
const newProducts = products.slice(0, 8);

export default function HomePage() {
  return (
    <div>
      {/* Hero Banner */}
      <section className="relative bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600&q=80')] bg-cover bg-center opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 md:py-36">
          <div className="max-w-2xl">
            <span className="inline-block bg-white/10 backdrop-blur-sm text-sm px-4 py-1.5 rounded-full mb-6 border border-white/20">
              春季新品上线
            </span>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6 leading-tight">
              精选品质好物
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
                让生活更美好
              </span>
            </h1>
            <p className="text-lg text-gray-300 mb-8 max-w-lg">
              发现来自全球的优质商品，从科技数码到时尚穿搭，YOVUS 为您严选每一件好物。
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/products"
                className="bg-white text-black px-8 py-3 rounded-full font-medium hover:bg-gray-100 transition-colors"
              >
                立即选购
              </Link>
              <Link
                href="/products?category=电子产品"
                className="border border-white/30 text-white px-8 py-3 rounded-full font-medium hover:bg-white/10 transition-colors"
              >
                热门数码
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Category Highlights */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: "电子产品", icon: "📱", color: "from-blue-500 to-blue-600" },
            { name: "服饰", icon: "👗", color: "from-pink-500 to-rose-600" },
            { name: "家居", icon: "🏠", color: "from-amber-500 to-orange-600" },
            { name: "美妆", icon: "💄", color: "from-purple-500 to-violet-600" },
          ].map((cat) => (
            <Link
              key={cat.name}
              href={`/products?category=${cat.name}`}
              className={`bg-gradient-to-br ${cat.color} text-white rounded-2xl p-6 text-center hover:scale-105 transition-transform duration-300 shadow-lg`}
            >
              <span className="text-3xl mb-2 block">{cat.icon}</span>
              <span className="font-medium">{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">精选推荐</h2>
            <p className="text-gray-500 mt-1">为您挑选的热门好物</p>
          </div>
          <Link href="/products" className="text-sm font-medium text-blue-600 hover:text-blue-700 transition">
            查看全部 &rarr;
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          {featuredProducts.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      {/* Promo Banner */}
      <section className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">限时特惠 · 全场低至5折</h2>
          <p className="text-blue-100 mb-6">新用户注册即享首单立减50元，更多优惠等你来</p>
          <Link
            href="/products"
            className="inline-block bg-white text-blue-600 px-8 py-3 rounded-full font-medium hover:bg-gray-100 transition"
          >
            去抢购
          </Link>
        </div>
      </section>

      {/* New Arrivals */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">新品上市</h2>
            <p className="text-gray-500 mt-1">发现最新上架的好物</p>
          </div>
          <Link href="/products" className="text-sm font-medium text-blue-600 hover:text-blue-700 transition">
            查看全部 &rarr;
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          {newProducts.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      {/* Trust Badges */}
      <section className="bg-white border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { icon: "🚚", title: "免费配送", desc: "满99元包邮" },
              { icon: "🔄", title: "7天退换", desc: "无忧售后保障" },
              { icon: "✅", title: "正品保证", desc: "品质严格把控" },
              { icon: "💬", title: "24h客服", desc: "随时为您服务" },
            ].map((item) => (
              <div key={item.title}>
                <span className="text-2xl mb-2 block">{item.icon}</span>
                <h3 className="font-semibold text-gray-900">{item.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
