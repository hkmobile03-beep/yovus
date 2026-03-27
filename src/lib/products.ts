export interface Product {
  id: string;
  name: string;
  price: number;
  originalPrice?: number;
  description: string;
  image: string;
  category: string;
  rating: number;
  reviews: number;
  badge?: string;
  features?: string[];
}

export const categories = [
  "全部",
  "电子产品",
  "服饰",
  "家居",
  "美妆",
  "食品",
];

export const products: Product[] = [
  {
    id: "1",
    name: "无线降噪耳机 Pro",
    price: 899,
    originalPrice: 1299,
    description:
      "采用先进的主动降噪技术，40小时超长续航，Hi-Res认证音质，佩戴舒适轻盈。支持蓝牙5.3，多设备无缝切换。",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
    category: "电子产品",
    rating: 4.8,
    reviews: 2341,
    badge: "热卖",
    features: ["主动降噪", "40小时续航", "蓝牙5.3", "Hi-Res认证"],
  },
  {
    id: "2",
    name: "智能运动手表 X5",
    price: 1599,
    originalPrice: 1999,
    description:
      "1.43寸AMOLED高清屏幕，100+运动模式，血氧心率监测，14天超长续航。IP68防水，支持NFC支付。",
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80",
    category: "电子产品",
    rating: 4.6,
    reviews: 1856,
    badge: "新品",
    features: ["AMOLED屏幕", "100+运动模式", "血氧监测", "14天续航"],
  },
  {
    id: "3",
    name: "轻奢羊绒大衣",
    price: 2680,
    originalPrice: 3580,
    description:
      "100%精选羊绒面料，双面手工缝制，经典翻领设计，修身版型，秋冬必备单品。",
    image: "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600&q=80",
    category: "服饰",
    rating: 4.9,
    reviews: 678,
    badge: "精选",
    features: ["100%羊绒", "双面工艺", "经典版型", "手工缝制"],
  },
  {
    id: "4",
    name: "北欧简约台灯",
    price: 359,
    originalPrice: 459,
    description:
      "极简设计风格，三档色温调节，无频闪护眼，触控操作，USB-C充电，适合书房卧室。",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&q=80",
    category: "家居",
    rating: 4.7,
    reviews: 1234,
    features: ["三档色温", "无频闪护眼", "触控操作", "USB-C充电"],
  },
  {
    id: "5",
    name: "天然植物护肤套装",
    price: 498,
    originalPrice: 698,
    description:
      "包含洁面乳、精华液、面霜三件套，天然植物萃取，温和不刺激，适合所有肤质。",
    image: "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=600&q=80",
    category: "美妆",
    rating: 4.5,
    reviews: 3210,
    badge: "畅销",
    features: ["天然植物", "三件套装", "温和配方", "全肤质适用"],
  },
  {
    id: "6",
    name: "有机坚果礼盒",
    price: 168,
    originalPrice: 238,
    description:
      "精选6种进口有机坚果，独立小包装，新鲜烘焙，无添加剂，送礼自用皆宜。",
    image: "https://images.unsplash.com/photo-1599599810694-b5b37304c041?w=600&q=80",
    category: "食品",
    rating: 4.8,
    reviews: 5678,
    features: ["6种坚果", "有机认证", "独立包装", "新鲜烘焙"],
  },
  {
    id: "7",
    name: "便携蓝牙音箱",
    price: 399,
    originalPrice: 549,
    description:
      "360°环绕立体声，IPX7防水，20小时续航，小巧便携，支持TWS双联。",
    image: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80",
    category: "电子产品",
    rating: 4.4,
    reviews: 987,
    features: ["360°环绕声", "IPX7防水", "20小时续航", "TWS双联"],
  },
  {
    id: "8",
    name: "真丝连衣裙",
    price: 1280,
    originalPrice: 1680,
    description:
      "100%桑蚕丝面料，优雅垂感，法式复古印花设计，适合春夏通勤与日常穿搭。",
    image: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=600&q=80",
    category: "服饰",
    rating: 4.7,
    reviews: 456,
    badge: "新品",
    features: ["100%桑蚕丝", "法式印花", "优雅垂感", "春夏适穿"],
  },
  {
    id: "9",
    name: "智能香薰机",
    price: 289,
    description:
      "超声波雾化，7色氛围灯，定时功能，静音运行，300ml大容量，精油扩香。",
    image: "https://images.unsplash.com/photo-1602928321679-560bb453f190?w=600&q=80",
    category: "家居",
    rating: 4.6,
    reviews: 2100,
    features: ["超声波雾化", "7色氛围灯", "定时功能", "300ml容量"],
  },
  {
    id: "10",
    name: "男士商务皮带",
    price: 458,
    originalPrice: 598,
    description:
      "头层牛皮，自动扣设计，百搭商务风格，做工精细，送礼佳品。",
    image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80",
    category: "服饰",
    rating: 4.5,
    reviews: 789,
    features: ["头层牛皮", "自动扣", "商务百搭", "精细做工"],
  },
  {
    id: "11",
    name: "进口精品咖啡豆",
    price: 128,
    originalPrice: 168,
    description:
      "哥伦比亚单品咖啡豆，中度烘焙，果香浓郁，酸甜平衡，250g精装。",
    image: "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&q=80",
    category: "食品",
    rating: 4.9,
    reviews: 3456,
    badge: "好评如潮",
    features: ["哥伦比亚产区", "中度烘焙", "果香浓郁", "250g精装"],
  },
  {
    id: "12",
    name: "保湿精华面膜",
    price: 89,
    originalPrice: 129,
    description:
      "玻尿酸深层补水，蚕丝面膜布，15分钟急救补水，一盒10片装。",
    image: "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=600&q=80",
    category: "美妆",
    rating: 4.3,
    reviews: 8901,
    badge: "销量冠军",
    features: ["玻尿酸配方", "蚕丝膜布", "15分钟急救", "10片装"],
  },
];

export function getProductById(id: string): Product | undefined {
  return products.find((p) => p.id === id);
}

export function getProductsByCategory(category: string): Product[] {
  if (category === "全部") return products;
  return products.filter((p) => p.category === category);
}
