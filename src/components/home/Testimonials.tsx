import { Star, Quote } from "lucide-react";
import ScrollReveal from "@/components/ui/ScrollReveal";

const testimonials = [
  {
    name: "Tanaka Yuki",
    location: "Tokyo",
    rating: 5,
    text: "I've tried many mattresses over the years, but YOVUS is on another level. The hybrid design gives perfect support while still feeling incredibly soft. Best sleep I've had in years.",
    product: "YOVUS Mattress (Double)",
  },
  {
    name: "Sato Mika",
    location: "Osaka",
    rating: 5,
    text: "Was skeptical about ordering a mattress online, but the 120-day trial convinced me. By the second week, I knew I'd never return it. My back pain has significantly improved!",
    product: "YOVUS Mattress (Queen)",
  },
  {
    name: "Yamamoto Ken",
    location: "Fukuoka",
    rating: 5,
    text: "The fold mattress is perfect for our guest room. Comfortable enough for everyday use but stores away easily. Our guests always comment on how well they slept.",
    product: "YOVUS Fold Mattress",
  },
  {
    name: "Kobayashi Aoi",
    location: "Nagoya",
    rating: 4,
    text: "Love the memory foam pillow! It contours perfectly to my neck and I no longer wake up with stiffness. The TENCEL cover is so soft too. Great quality for the price.",
    product: "YOVUS Memory Foam Pillow",
  },
];

export default function Testimonials() {
  return (
    <section className="py-16 md:py-24 bg-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="text-center mb-12">
            <span className="text-primary text-sm font-medium uppercase tracking-wider">
              Reviews
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-secondary mt-2 mb-4">
              What Our Customers Say
            </h2>
            <p className="text-secondary/60 max-w-2xl mx-auto">
              98% satisfaction rate across 130,000+ units sold.
              Here&apos;s what real customers think.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {testimonials.map((testimonial, index) => (
            <ScrollReveal key={testimonial.name} delay={index * 100}>
              <div className="bg-white rounded-card p-6 card-shadow h-full flex flex-col">
                <Quote className="text-primary/20 mb-3" size={28} />
                <p className="text-secondary/70 text-sm leading-relaxed flex-1 mb-4">
                  &ldquo;{testimonial.text}&rdquo;
                </p>
                <div className="flex mb-2">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      size={14}
                      className={
                        i < testimonial.rating
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-gray-200"
                      }
                    />
                  ))}
                </div>
                <div>
                  <div className="font-semibold text-secondary text-sm">
                    {testimonial.name}
                  </div>
                  <div className="text-xs text-secondary/50">
                    {testimonial.location} · {testimonial.product}
                  </div>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
