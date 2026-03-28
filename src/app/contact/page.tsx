"use client";

import { useState } from "react";
import ScrollReveal from "@/components/ui/ScrollReveal";
import Button from "@/components/ui/Button";
import { Mail, Phone, MapPin, Clock, Send, MessageSquare } from "lucide-react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-to-r from-section to-cream py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-3xl md:text-4xl font-bold text-secondary mb-3">
            Get in Touch
          </h1>
          <p className="text-secondary/60 max-w-xl mx-auto">
            Have a question about our products or need help with your order?
            We&apos;re here to help.
          </p>
        </div>
      </section>

      <section className="py-12 md:py-16 bg-cream-light">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Contact Info */}
            <ScrollReveal>
              <div className="space-y-6">
                <div className="bg-white rounded-card p-6 card-shadow">
                  <h3 className="font-semibold text-secondary mb-4">
                    Contact Information
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Mail className="text-primary" size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-secondary">
                          Email
                        </div>
                        <div className="text-sm text-secondary/60">
                          hello@yovus.com
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Phone className="text-primary" size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-secondary">
                          Phone
                        </div>
                        <div className="text-sm text-secondary/60">
                          0120-000-000
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <MapPin className="text-primary" size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-secondary">
                          Address
                        </div>
                        <div className="text-sm text-secondary/60">
                          Tokyo, Japan
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Clock className="text-primary" size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-secondary">
                          Business Hours
                        </div>
                        <div className="text-sm text-secondary/60">
                          Mon-Fri 10:00-18:00 (JST)
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-primary/5 rounded-card p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageSquare className="text-primary" size={18} />
                    <h3 className="font-semibold text-secondary">
                      Quick Response
                    </h3>
                  </div>
                  <p className="text-sm text-secondary/60">
                    We typically respond within 24 hours on business days.
                    For urgent matters, please call us directly.
                  </p>
                </div>
              </div>
            </ScrollReveal>

            {/* Contact Form */}
            <ScrollReveal delay={100}>
              <div className="lg:col-span-2">
                {submitted ? (
                  <div className="bg-white rounded-card p-12 card-shadow text-center">
                    <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
                      <Send className="text-green-600" size={28} />
                    </div>
                    <h2 className="text-2xl font-bold text-secondary mb-2">
                      Message Sent!
                    </h2>
                    <p className="text-secondary/60">
                      Thank you for reaching out. We&apos;ll get back to you
                      within 24 hours.
                    </p>
                    <button
                      onClick={() => setSubmitted(false)}
                      className="mt-6 text-primary hover:underline text-sm"
                    >
                      Send another message
                    </button>
                  </div>
                ) : (
                  <form
                    onSubmit={handleSubmit}
                    className="bg-white rounded-card p-6 md:p-8 card-shadow"
                  >
                    <h2 className="text-xl font-bold text-secondary mb-6">
                      Send us a Message
                    </h2>

                    <div className="grid sm:grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-secondary mb-1.5">
                          Name
                        </label>
                        <input
                          type="text"
                          required
                          className="w-full px-4 py-3 border-2 border-cream rounded-soft focus:border-primary focus:outline-none transition-colors text-sm"
                          placeholder="Your name"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-secondary mb-1.5">
                          Email
                        </label>
                        <input
                          type="email"
                          required
                          className="w-full px-4 py-3 border-2 border-cream rounded-soft focus:border-primary focus:outline-none transition-colors text-sm"
                          placeholder="you@example.com"
                        />
                      </div>
                    </div>

                    <div className="mb-4">
                      <label className="block text-sm font-medium text-secondary mb-1.5">
                        Subject
                      </label>
                      <select className="w-full px-4 py-3 border-2 border-cream rounded-soft focus:border-primary focus:outline-none transition-colors text-sm text-secondary">
                        <option value="">Select a topic</option>
                        <option value="order">Order Inquiry</option>
                        <option value="product">Product Question</option>
                        <option value="return">Returns & Trial</option>
                        <option value="warranty">Warranty</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <div className="mb-6">
                      <label className="block text-sm font-medium text-secondary mb-1.5">
                        Message
                      </label>
                      <textarea
                        required
                        rows={5}
                        className="w-full px-4 py-3 border-2 border-cream rounded-soft focus:border-primary focus:outline-none transition-colors text-sm resize-none"
                        placeholder="Tell us how we can help..."
                      />
                    </div>

                    <Button type="submit" size="lg" className="w-full sm:w-auto">
                      <Send size={16} className="mr-2" /> Send Message
                    </Button>
                  </form>
                )}
              </div>
            </ScrollReveal>
          </div>
        </div>
      </section>
    </>
  );
}
