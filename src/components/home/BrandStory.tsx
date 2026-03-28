import Link from "next/link";
import Button from "@/components/ui/Button";
import ScrollReveal from "@/components/ui/ScrollReveal";

export default function BrandStory() {
  return (
    <section className="py-16 md:py-24 bg-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Image Side */}
          <ScrollReveal>
            <div className="relative">
              <div className="bg-white rounded-3xl overflow-hidden card-shadow aspect-[4/3] flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-warm to-warm-dark rounded-3xl flex items-center justify-center">
                    <span className="text-5xl">🏭</span>
                  </div>
                  <p className="text-secondary/60 text-sm">
                    Handcrafted in our own factory
                  </p>
                </div>
              </div>
              <div className="absolute -bottom-6 -right-6 bg-primary text-white p-6 rounded-2xl card-shadow">
                <div className="text-3xl font-bold">Since</div>
                <div className="text-lg">2018</div>
              </div>
            </div>
          </ScrollReveal>

          {/* Text Side */}
          <ScrollReveal delay={200}>
            <div>
              <span className="text-primary text-sm font-medium uppercase tracking-wider">
                Our Story
              </span>
              <h2 className="text-3xl md:text-4xl font-bold text-secondary mt-2 mb-6">
                Born from a Simple Wish:
                <br />
                <span className="text-primary">Better Sleep for Everyone</span>
              </h2>
              <div className="space-y-4 text-secondary/70 leading-relaxed">
                <p>
                  YOVUS was born in 2018 from a founder&apos;s desire to find a
                  better mattress for their family. Collaborating with engineers
                  and designers, we developed a revolutionary hybrid mattress
                  that combines the best of foam comfort and spring support.
                </p>
                <p>
                  Our crowdfunding campaign raised over 6,000% of its goal,
                  proving that people everywhere crave better sleep. Today,
                  we&apos;ve sold over 130,000 units and continue to innovate
                  with the same passion.
                </p>
                <p>
                  Every YOVUS product is handcrafted in our own factory and
                  shipped directly to you — no middlemen, no markups, just
                  honest quality at a fair price.
                </p>
              </div>
              <Link href="/about" className="inline-block mt-8">
                <Button variant="outline">Learn More</Button>
              </Link>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}
