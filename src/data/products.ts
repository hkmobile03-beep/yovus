export interface Product {
  id: string;
  slug: string;
  name: string;
  nameJa: string;
  category: string;
  description: string;
  descriptionJa: string;
  price: number;
  originalPrice?: number;
  sizes?: ProductSize[];
  features: string[];
  images: string[];
  badge?: string;
  rating: number;
  reviewCount: number;
  inStock: boolean;
}

export interface ProductSize {
  name: string;
  dimensions: string;
  price: number;
  weight?: string;
}

export const categories = [
  { id: "all", name: "All Products", nameJa: "すべて" },
  { id: "mattress", name: "Mattress", nameJa: "マットレス" },
  { id: "pillow", name: "Pillow", nameJa: "まくら" },
  { id: "bedding", name: "Bedding", nameJa: "寝具" },
  { id: "accessories", name: "Accessories", nameJa: "アクセサリー" },
];

export const products: Product[] = [
  {
    id: "1",
    slug: "yovus-mattress",
    name: "YOVUS Mattress",
    nameJa: "YOVUS マットレス",
    category: "mattress",
    description:
      "Our signature hybrid mattress combining premium urethane foam with independent coil springs. 6cm of high-polymer resilience foam for unparalleled comfort and support.",
    descriptionJa:
      "独自開発の高分子弾力ウレタンフォームと独立コイルスプリングを組み合わせたハイブリッドマットレス。6cmの贅沢なフォームで至高の寝心地を実現。",
    price: 79800,
    sizes: [
      { name: "Single", dimensions: "97×195×26cm", price: 79800, weight: "35kg" },
      { name: "Semi-Double", dimensions: "120×195×26cm", price: 89800, weight: "36kg" },
      { name: "Double", dimensions: "140×195×26cm", price: 99800, weight: "46kg" },
      { name: "Queen", dimensions: "160×195×26cm", price: 109800, weight: "51kg" },
    ],
    features: [
      "Hybrid design: urethane foam + coil springs",
      "6cm high-polymer resilience foam",
      "Breathable grid-cut surface design",
      "100% TENCEL lyocell fabric cover",
      "120-day free trial",
      "10-year warranty",
    ],
    images: [
      "/images/mattress-1.jpg",
      "/images/mattress-2.jpg",
      "/images/mattress-3.jpg",
      "/images/mattress-4.jpg",
    ],
    badge: "BEST SELLER",
    rating: 4.8,
    reviewCount: 2450,
    inStock: true,
  },
  {
    id: "2",
    slug: "yovus-fold",
    name: "YOVUS Fold Mattress",
    nameJa: "YOVUS フォールド マットレス",
    category: "mattress",
    description:
      "A tri-fold portable mattress with high-resilience foam. Perfect for guest rooms, naps, and small spaces. Easy to store and transport.",
    descriptionJa:
      "三つ折りポータブルマットレス。高反発フォーム採用で、来客用・お昼寝・コンパクトスペースに最適。収納・持ち運びも簡単。",
    price: 39800,
    sizes: [
      { name: "Single", dimensions: "97×195×10cm", price: 39800, weight: "7kg" },
      { name: "Semi-Double", dimensions: "120×195×10cm", price: 45800, weight: "9kg" },
    ],
    features: [
      "Tri-fold compact design",
      "High-resilience urethane foam",
      "Removable washable cover",
      "Anti-slip bottom",
      "120-day free trial",
    ],
    images: [
      "/images/fold-1.jpg",
      "/images/fold-2.jpg",
      "/images/fold-3.jpg",
    ],
    badge: "NEW",
    rating: 4.7,
    reviewCount: 890,
    inStock: true,
  },
  {
    id: "3",
    slug: "yovus-memory-pillow",
    name: "YOVUS Memory Foam Pillow",
    nameJa: "YOVUS 低反発フォームまくら",
    category: "pillow",
    description:
      "Ergonomically designed memory foam pillow that contours to your head and neck for optimal support. Features a breathable open-cell structure.",
    descriptionJa:
      "人間工学に基づいた低反発フォームまくら。頭と首に沿ってフィットし、最適なサポートを提供。通気性のあるオープンセル構造。",
    price: 9800,
    features: [
      "Ergonomic contour design",
      "Breathable memory foam",
      "Removable TENCEL cover",
      "Hypoallergenic",
      "Washable cover",
    ],
    images: [
      "/images/pillow-1.jpg",
      "/images/pillow-2.jpg",
    ],
    rating: 4.6,
    reviewCount: 1230,
    inStock: true,
  },
  {
    id: "4",
    slug: "yovus-comforter",
    name: "YOVUS Reversible Comforter",
    nameJa: "YOVUS リバーシブル布団",
    category: "bedding",
    description:
      "A lightweight, all-season reversible comforter with hollow-fiber technology. Cool side for summer, warm side for winter.",
    descriptionJa:
      "軽量オールシーズン対応のリバーシブル布団。中空繊維テクノロジーで夏は涼しく、冬は暖かく。",
    price: 19800,
    sizes: [
      { name: "Single", dimensions: "150×210cm", price: 19800 },
      { name: "Double", dimensions: "190×210cm", price: 25800 },
    ],
    features: [
      "Reversible warm/cool design",
      "Hollow-fiber fill technology",
      "100% cruelty-free materials",
      "Machine washable",
      "Lightweight and breathable",
    ],
    images: [
      "/images/comforter-1.jpg",
      "/images/comforter-2.jpg",
    ],
    rating: 4.5,
    reviewCount: 680,
    inStock: true,
  },
  {
    id: "5",
    slug: "yovus-mattress-pad",
    name: "YOVUS Fitted Mattress Pad",
    nameJa: "YOVUS 敷きパッド",
    category: "bedding",
    description:
      "A premium fitted mattress pad with waterproof membrane and soft cotton surface. Protects your mattress while adding extra comfort.",
    descriptionJa:
      "防水メンブレン付きプレミアム敷きパッド。柔らかいコットン表面でマットレスを保護しながら快適さをプラス。",
    price: 12800,
    sizes: [
      { name: "Single", dimensions: "97×195cm", price: 12800 },
      { name: "Semi-Double", dimensions: "120×195cm", price: 14800 },
      { name: "Double", dimensions: "140×195cm", price: 16800 },
      { name: "Queen", dimensions: "160×195cm", price: 18800 },
    ],
    features: [
      "Waterproof membrane layer",
      "Soft cotton top surface",
      "Deep pocket elastic fit",
      "Machine washable",
      "Noiseless design",
    ],
    images: [
      "/images/pad-1.jpg",
      "/images/pad-2.jpg",
    ],
    rating: 4.4,
    reviewCount: 520,
    inStock: true,
  },
  {
    id: "6",
    slug: "yovus-gauze-sheets",
    name: "YOVUS Gauze Sheet Set",
    nameJa: "YOVUS ガーゼシーツセット",
    category: "bedding",
    description:
      "Ultra-soft triple-layered gauze sheet set. Gets softer with every wash. Includes fitted sheet and two pillowcases.",
    descriptionJa:
      "超柔らかい三重ガーゼシーツセット。洗うたびに柔らかく。フィットシーツとまくらカバー2枚のセット。",
    price: 15800,
    sizes: [
      { name: "Single", dimensions: "97×195cm", price: 15800 },
      { name: "Double", dimensions: "140×195cm", price: 19800 },
    ],
    features: [
      "Triple-layered gauze construction",
      "Gets softer with each wash",
      "Breathable and moisture-wicking",
      "Includes 2 pillowcases",
      "OEKO-TEX certified",
    ],
    images: [
      "/images/sheets-1.jpg",
      "/images/sheets-2.jpg",
    ],
    badge: "NEW",
    rating: 4.7,
    reviewCount: 340,
    inStock: true,
  },
  {
    id: "7",
    slug: "yovus-sleep-mask",
    name: "YOVUS Silk Sleep Mask",
    nameJa: "YOVUS シルクアイマスク",
    category: "accessories",
    description:
      "100% mulberry silk sleep mask with adjustable strap. Blocks light completely for deeper sleep.",
    descriptionJa:
      "100%マルベリーシルクのアイマスク。調整可能なストラップで完全遮光。より深い睡眠へ。",
    price: 3800,
    features: [
      "100% mulberry silk",
      "Complete light blocking",
      "Adjustable elastic strap",
      "Breathable and gentle on skin",
    ],
    images: [
      "/images/mask-1.jpg",
      "/images/mask-2.jpg",
    ],
    rating: 4.3,
    reviewCount: 890,
    inStock: true,
  },
  {
    id: "8",
    slug: "yovus-aromatherapy-spray",
    name: "YOVUS Sleep Mist",
    nameJa: "YOVUS スリープミスト",
    category: "accessories",
    description:
      "Calming lavender and chamomile pillow mist to help you drift off naturally. Made with essential oils.",
    descriptionJa:
      "ラベンダーとカモミールのピローミスト。天然エッセンシャルオイル使用で自然な眠りへ。",
    price: 2800,
    features: [
      "Natural essential oils",
      "Lavender and chamomile blend",
      "50ml spray bottle",
      "Non-staining formula",
    ],
    images: [
      "/images/mist-1.jpg",
      "/images/mist-2.jpg",
    ],
    rating: 4.5,
    reviewCount: 450,
    inStock: true,
  },
];

export function getProductBySlug(slug: string): Product | undefined {
  return products.find((p) => p.slug === slug);
}

export function getProductsByCategory(category: string): Product[] {
  if (category === "all") return products;
  return products.filter((p) => p.category === category);
}

export function getRelatedProducts(productId: string, limit = 4): Product[] {
  const product = products.find((p) => p.id === productId);
  if (!product) return [];
  return products
    .filter((p) => p.id !== productId && p.category === product.category)
    .slice(0, limit);
}
