import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-white text-lg font-bold mb-4">YOVUS</h3>
            <p className="text-sm text-gray-400">
              精选品质好物，让生活更美好。我们致力于为您提供最优质的购物体验。
            </p>
          </div>
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">商品分类</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/products?category=电子产品" className="hover:text-white transition">电子产品</Link></li>
              <li><Link href="/products?category=服饰" className="hover:text-white transition">服饰</Link></li>
              <li><Link href="/products?category=家居" className="hover:text-white transition">家居</Link></li>
              <li><Link href="/products?category=美妆" className="hover:text-white transition">美妆</Link></li>
              <li><Link href="/products?category=食品" className="hover:text-white transition">食品</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">客户服务</h4>
            <ul className="space-y-2 text-sm">
              <li><span className="hover:text-white transition cursor-pointer">帮助中心</span></li>
              <li><span className="hover:text-white transition cursor-pointer">退换货政策</span></li>
              <li><span className="hover:text-white transition cursor-pointer">配送说明</span></li>
              <li><span className="hover:text-white transition cursor-pointer">联系我们</span></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">关于我们</h4>
            <ul className="space-y-2 text-sm">
              <li><span className="hover:text-white transition cursor-pointer">品牌故事</span></li>
              <li><span className="hover:text-white transition cursor-pointer">加入我们</span></li>
              <li><span className="hover:text-white transition cursor-pointer">隐私政策</span></li>
              <li><span className="hover:text-white transition cursor-pointer">用户协议</span></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-gray-800 text-center text-sm text-gray-500">
          &copy; 2026 YOVUS. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
