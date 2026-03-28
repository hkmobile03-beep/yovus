import Hero from "@/components/home/Hero";
import TrustBar from "@/components/home/TrustBar";
import FeaturedProducts from "@/components/home/FeaturedProducts";
import BrandStory from "@/components/home/BrandStory";
import ProductFeatures from "@/components/home/ProductFeatures";
import Testimonials from "@/components/home/Testimonials";
import Newsletter from "@/components/home/Newsletter";
import InstagramFeed from "@/components/home/InstagramFeed";

export default function Home() {
  return (
    <>
      <Hero />
      <TrustBar />
      <FeaturedProducts />
      <BrandStory />
      <ProductFeatures />
      <Testimonials />
      <InstagramFeed />
      <Newsletter />
    </>
  );
}
