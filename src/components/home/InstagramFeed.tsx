import ScrollReveal from "@/components/ui/ScrollReveal";
import { Camera } from "lucide-react";

const feedItems = [
  { emoji: "🛏️", bg: "from-primary/10 to-cream" },
  { emoji: "😴", bg: "from-warm to-warm-light" },
  { emoji: "🌿", bg: "from-green-50 to-cream" },
  { emoji: "☕", bg: "from-warm-dark/20 to-cream" },
  { emoji: "🏠", bg: "from-blue-50 to-cream" },
  { emoji: "✨", bg: "from-yellow-50 to-cream" },
];

export default function CameraFeed() {
  return (
    <section className="py-16 md:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="text-center mb-10">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Camera className="text-primary" size={20} />
              <span className="text-primary text-sm font-medium">
                @yovus_official
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-secondary">
              Follow Us on Camera
            </h2>
          </div>
        </ScrollReveal>

        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {feedItems.map((item, index) => (
            <ScrollReveal key={index} delay={index * 50}>
              <a
                href="#"
                className="aspect-square rounded-card overflow-hidden group relative"
              >
                <div
                  className={`w-full h-full bg-gradient-to-br ${item.bg} flex items-center justify-center`}
                >
                  <span className="text-3xl md:text-4xl group-hover:scale-110 transition-transform duration-300">
                    {item.emoji}
                  </span>
                </div>
                <div className="absolute inset-0 bg-primary/0 group-hover:bg-primary/20 transition-colors duration-300 flex items-center justify-center">
                  <Camera
                    className="text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    size={24}
                  />
                </div>
              </a>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
