import ScrollReveal from "@/components/ui/ScrollReveal";
import { Heart, Target, Users, Leaf } from "lucide-react";

const milestones = [
  { year: "2018", event: "Founded with a mission to revolutionize sleep" },
  { year: "2019", event: "Crowdfunding raised 6,000% of goal" },
  { year: "2020", event: "Annual sales exceeded 10,000 units" },
  { year: "2021", event: "Expanded to international markets" },
  { year: "2023", event: "Launched next-generation hybrid mattress" },
  { year: "2025", event: "Opened first flagship experience store" },
];

const values = [
  {
    icon: Heart,
    title: "Quality First",
    description:
      "Every product is handcrafted in our own factory with premium materials and rigorous quality control.",
  },
  {
    icon: Target,
    title: "Direct to You",
    description:
      "No middlemen, no retail markups. We ship directly from our factory to your doorstep.",
  },
  {
    icon: Leaf,
    title: "Sustainable",
    description:
      "100% cruelty-free materials and eco-friendly manufacturing processes.",
  },
  {
    icon: Users,
    title: "Customer Focused",
    description:
      "120-day trial, free shipping, 10-year warranty. We stand behind everything we make.",
  },
];

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-to-br from-warm-light via-cream-light to-section py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <ScrollReveal>
            <span className="text-primary text-sm font-medium uppercase tracking-wider">
              About YOVUS
            </span>
            <h1 className="text-4xl md:text-5xl font-bold text-secondary mt-3 mb-6">
              Making the World
              <br />
              <span className="gradient-text">Sleep Better</span>
            </h1>
            <p className="text-lg text-secondary/70 max-w-2xl mx-auto leading-relaxed">
              Born from a simple wish to find the perfect mattress, YOVUS has
              grown into a movement. We believe everyone deserves deep,
              restorative sleep — without compromising on quality or breaking
              the bank.
            </p>
          </ScrollReveal>
        </div>
      </section>

      {/* Story */}
      <section className="py-16 md:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <ScrollReveal>
              <div className="bg-section rounded-3xl aspect-[4/3] flex items-center justify-center card-shadow">
                <div className="text-center p-8">
                  <div className="w-28 h-28 mx-auto mb-4 bg-gradient-to-br from-primary/20 to-warm rounded-3xl flex items-center justify-center animate-float">
                    <span className="text-6xl">💭</span>
                  </div>
                  <p className="text-secondary/50 text-sm">
                    Where it all began
                  </p>
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal delay={200}>
              <h2 className="text-3xl font-bold text-secondary mb-6">
                Our Story
              </h2>
              <div className="space-y-4 text-secondary/70 leading-relaxed">
                <p>
                  In 2018, our founder set out on a simple mission: find a
                  mattress that would give their family the best sleep
                  possible. After testing dozens of options and finding none
                  that truly delivered, they decided to create one.
                </p>
                <p>
                  Working with sleep engineers and industrial designers, we
                  developed a revolutionary hybrid mattress that combines the
                  pressure-relieving comfort of premium foam with the
                  supportive bounce of independent coil springs.
                </p>
                <p>
                  When we launched our crowdfunding campaign, the response
                  was overwhelming — raising 6,000% of our original goal.
                  That&apos;s when we knew we weren&apos;t just making a
                  mattress. We were starting a movement.
                </p>
                <p>
                  Today, with over 130,000 units sold and a 98% satisfaction
                  rate, YOVUS continues to innovate with the same passion
                  and commitment to quality that started it all.
                </p>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-16 md:py-24 bg-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-secondary mb-4">
                Our Values
              </h2>
              <p className="text-secondary/60 max-w-xl mx-auto">
                Everything we do is guided by four core principles.
              </p>
            </div>
          </ScrollReveal>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {values.map((value, index) => (
              <ScrollReveal key={value.title} delay={index * 100}>
                <div className="bg-white rounded-card p-6 card-shadow text-center h-full">
                  <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <value.icon className="text-primary" size={24} />
                  </div>
                  <h3 className="text-lg font-semibold text-secondary mb-2">
                    {value.title}
                  </h3>
                  <p className="text-secondary/60 text-sm leading-relaxed">
                    {value.description}
                  </p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-16 md:py-24 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-secondary mb-4">
                Our Journey
              </h2>
            </div>
          </ScrollReveal>

          <div className="space-y-0">
            {milestones.map((milestone, index) => (
              <ScrollReveal key={milestone.year} delay={index * 100}>
                <div className="flex gap-6 items-start pb-8 last:pb-0">
                  <div className="flex flex-col items-center">
                    <div className="w-12 h-12 bg-primary text-white rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0">
                      {milestone.year.slice(2)}
                    </div>
                    {index < milestones.length - 1 && (
                      <div className="w-0.5 h-full bg-primary/20 mt-2 min-h-[2rem]" />
                    )}
                  </div>
                  <div className="pt-2.5">
                    <div className="text-sm font-semibold text-primary mb-1">
                      {milestone.year}
                    </div>
                    <p className="text-secondary/70">{milestone.event}</p>
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 md:py-20 bg-gradient-to-r from-primary to-primary-dark text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <ScrollReveal>
              <div>
                <div className="text-4xl md:text-5xl font-bold">130K+</div>
                <div className="text-white/70 mt-1">Units Sold</div>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={100}>
              <div>
                <div className="text-4xl md:text-5xl font-bold">98%</div>
                <div className="text-white/70 mt-1">Satisfaction</div>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={200}>
              <div>
                <div className="text-4xl md:text-5xl font-bold">10yr</div>
                <div className="text-white/70 mt-1">Warranty</div>
              </div>
            </ScrollReveal>
            <ScrollReveal delay={300}>
              <div>
                <div className="text-4xl md:text-5xl font-bold">5+</div>
                <div className="text-white/70 mt-1">Countries</div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>
    </>
  );
}
