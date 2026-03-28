import { Truck, Shield, Clock, CreditCard } from "lucide-react";
import ScrollReveal from "@/components/ui/ScrollReveal";

const trustItems = [
  {
    icon: Clock,
    title: "120-Day Trial",
    description: "Try risk-free at home",
  },
  {
    icon: Truck,
    title: "Free Shipping",
    description: "Delivered to your door",
  },
  {
    icon: Shield,
    title: "10-Year Warranty",
    description: "Quality guaranteed",
  },
  {
    icon: CreditCard,
    title: "3 Installments",
    description: "Interest-free payments",
  },
];

export default function TrustBar() {
  return (
    <section className="bg-white border-y border-cream">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {trustItems.map((item, index) => (
            <ScrollReveal key={item.title} delay={index * 100}>
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <item.icon className="text-primary" size={22} />
                </div>
                <div>
                  <h4 className="font-semibold text-secondary text-sm">
                    {item.title}
                  </h4>
                  <p className="text-secondary/60 text-xs mt-0.5">
                    {item.description}
                  </p>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
