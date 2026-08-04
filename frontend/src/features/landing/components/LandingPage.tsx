import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight } from "lucide-react";
import SiteHeader from "../../../components/layout/SiteHeader";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=2400&q=80";

export default function LandingPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen">
      <SiteHeader />

      <section className="relative isolate min-h-[calc(100vh-var(--header-h))] overflow-hidden">
        <img
          src={HERO_IMAGE}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
          fetchPriority="high"
        />
        <div
          className="absolute inset-0 bg-gradient-to-r from-[var(--color-teal-950)]/92 via-[var(--color-teal-900)]/78 to-teal-900/35"
          aria-hidden
        />
        <div
          className="absolute inset-0 bg-gradient-to-t from-[var(--color-teal-950)]/55 via-transparent to-transparent"
          aria-hidden
        />

        <div className="relative mx-auto flex min-h-[calc(100vh-var(--header-h))] max-w-6xl flex-col justify-end px-5 pb-16 pt-20 sm:justify-center sm:px-8 sm:pb-24 sm:pt-12">
          <div className="max-w-xl animate-fade-up text-white">
            <h1 className="font-display text-5xl leading-[1.05] tracking-tight sm:text-6xl md:text-7xl">
              {t("brand")}
            </h1>
            <p className="mt-5 max-w-md font-body text-xl font-normal leading-snug text-teal-50/95 sm:text-2xl">
              {t("landing.headline")}
            </p>
            <p className="mt-4 max-w-sm text-base leading-relaxed text-teal-100/80">
              {t("landing.support")}
            </p>
            <div className="mt-8">
              <Link
                to="/detect"
                className="cta-lift inline-flex items-center gap-2 rounded-lg bg-[var(--color-seafoam)] px-6 py-3 text-base font-semibold text-[var(--color-teal-950)]"
              >
                {t("landing.cta")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-teal-900/8 bg-white/40">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 sm:py-20">
          <div className="max-w-2xl animate-fade-in">
            <h2 className="text-3xl text-[var(--color-teal-950)] sm:text-4xl">
              {t("landing.sectionTitle")}
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-[var(--color-muted)]">
              {t("landing.sectionBody")}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
