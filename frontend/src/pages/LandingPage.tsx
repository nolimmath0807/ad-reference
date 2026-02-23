import { Navbar } from "@/components/landing/Navbar"
import { HeroSection } from "@/components/landing/HeroSection"
import { StatsSection } from "@/components/landing/StatsSection"
import { FeatureSection } from "@/components/landing/FeatureSection"
import { TestimonialSection } from "@/components/landing/TestimonialSection"
import { CtaSection } from "@/components/landing/CtaSection"
import { Footer } from "@/components/landing/Footer"

function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main>
        <HeroSection />
        <StatsSection />
        <FeatureSection />
        <TestimonialSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  )
}

export default LandingPage
