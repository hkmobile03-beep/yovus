import { Layers, Wind, Leaf, Zap } from "lucide-react";
import ScrollReveal from "@/components/ui/ScrollReveal";

const features = [
  {
    icon: Layers,
    title: "Hybrid Design",
    description:
      "Premium urethane foam meets independent coil springs for the perfect balance of comfort and support.",
    color: "bg-primary/10 text-primary",
  },
  {
    icon: Zap,
    title: "High-Polymer Foam",
    description:
      "6cm of proprietary high-polymer resilience foam — 3x the industry standard for unmatched comfort.",
    color: "bg-warm text-orange-600",
  },
  {
    icon: Wind,
    title: "Breathable Surface",
    description:
      "Grid-cut surface design with TENCEL lyocell fabric wicks moisture and keeps you cool all night.",
    color: "bg-blue-50 text-blue-500",
  },
  {
    icon: Leaf,
    title: "Eco-Friendly",
    description:
      "100% cruelty-free materials with hollow-fiber technology. No animal products, no harmful chemicals.",
    color: "bg-green-50 text-green-600",
  },
];

export default function ProductFeatures() {
  return (
    <section className="py-16 md:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="text-center mb-12">
            <span className="text-primary text-sm font-medium uppercase tracking-wider">
              Why YOVUS
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-secondary mt-2 mb-4">
              Engineered for Better Sleep
            </h2>
            <p className="text-secondary/60 max-w-2xl mx-auto">
              Every detail is carefully designed to give you the deepest,
              most restful sleep of your life.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <ScrollReveal key={feature.title} delay={index * 100}>
              <div className="p-6 rounded-card bg-cream-light hover:bg-white hover:card-shadow-hover transition-all duration-300 h-full">
                <div
                  className={`w-12 h-12 rounded-xl ${feature.color} flex items-center justify-center mb-4`}
                >
                  <feature.icon size={22} />
                </div>
                <h3 className="text-lg font-semibold text-secondary mb-2">
                  {feature.title}
                </h3>
                <p className="text-secondary/60 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
