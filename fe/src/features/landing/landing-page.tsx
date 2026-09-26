"use client";

import Image from "next/image";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Languages, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useInventoryLanguage } from "@/components/providers/inventory-language-provider";
import theme from "@/components/inventory/aruna-theme.module.css";

const SLIDE_DURATION_MS = 5500;
export const LANDING_NAVBAR_SOLID_Y = 48;
export const LANDING_APP_HREF = "/ringkasan";
export function shouldUseSolidLandingNavbar(scrollY: number): boolean {
  return scrollY >= LANDING_NAVBAR_SOLID_Y;
}

const content = {
  en: {
    home: "Home", how: "How it works", features: "Features", start: "Start now", explore: "EXPLORE NOW!",
    navigation: "Landing navigation", switchLanguage: "Switch to Indonesian",
    previous: "Previous slide", next: "Next slide", pause: "Pause autoplay", resume: "Resume autoplay", slide: "Go to slide",
    howTitle: "From Sales to Production Plans",
    howDescription: "ARUNA turns sales and stock data into more measurable recommendations for production and ingredient procurement.",
    featureTitle: "Better-Planned Production, Better-Controlled Ingredients",
    featureDescription: "From sales forecasts to ingredient procurement, ARUNA helps juice businesses prepare for production more accurately.",
    ctaTitle: "Prepare Ingredients. Keep Production Running.",
    ctaDescription: "Turn demand forecasts into better production and restocking decisions with ARUNA.",
    cta: "OPTIMIZE YOUR PRODUCTION",
    slides: [
      ["Manage Juice Production", "Smarter", "Forecast demand, prepare ingredients, and plan production more accurately.", "Sales and inventory dashboard illustration"],
      ["Forecast Juice Demand", "Earlier", "ARUNA learns from sales patterns to estimate how much juice will be needed over the next few days. Production no longer has to rely on guesswork alone.", "Demand forecast illustration"],
      ["Understand Your", "Ingredient Needs More Accurately", "Demand forecasts are translated into requirements for fruit, milk, sugar, and other ingredients. Prepare what you need, in the right quantities.", "Ingredient requirements illustration"],
      ["Identify Risks", "Of Stock Shortages", "ARUNA compares production requirements with available stock to detect ingredients that may run out sooner. Take action before production is disrupted.", "Inventory risk illustration"],
      ["Determine When and", "How Much to Restock", "Get recommendations on which ingredients to buy, how much to purchase, and the best time to restock. Be ready for demand without holding excess stock.", "Procurement planning illustration"],
    ],
    steps: [
      ["Sales Data Comes In", "Juice transactions are recorded as the basis for demand analysis."],
      ["Forecast Demand", "ARUNA estimates how many of each juice menu item will be sold."],
      ["Calculate Ingredient Needs", "Sales forecasts are translated into requirements for each ingredient."],
      ["Detect Stock Risks", "Requirements are compared with available stock to identify potential shortages."],
      ["Restocking Recommendations", "ARUNA recommends which ingredients to buy, in what quantities, and when."],
      ["Production Plan", "The owner reviews recommendations and decides on the next production plan."],
    ],
    cards: [
      ["Demand Forecasting", "Estimate how many of each juice menu item will be needed over the next few days."],
      ["Ingredient Requirements", "Know how much fruit and other ingredients are needed to meet demand."],
      ["Stock Shortage Risks", "Identify ingredients that may be insufficient before they disrupt production."],
      ["Recommended Quantities", "Align purchase quantities with production needs and available stock."],
      ["Restocking Timing", "Know when ingredients need to be purchased so they are available when needed."],
    ],
  },
  id: {
    home: "Beranda", how: "Cara kerja", features: "Fitur", start: "Mulai sekarang", explore: "EXPLORE NOW!",
    navigation: "Navigasi landing page", switchLanguage: "Ganti ke bahasa Inggris",
    previous: "Slide sebelumnya", next: "Slide berikutnya", pause: "Jeda carousel otomatis", resume: "Lanjutkan carousel otomatis", slide: "Buka slide",
    howTitle: "Dari Penjualan Menjadi Rencana Produksi",
    howDescription: "ARUNA mengubah data penjualan dan stok menjadi rekomendasi produksi dan pengadaan bahan baku yang lebih terukur.",
    featureTitle: "Produksi Lebih Terencana, Bahan Lebih Terkendali",
    featureDescription: "Dari prediksi penjualan hingga pengadaan bahan baku, ARUNA membantu bisnis jus mempersiapkan produksi dengan lebih tepat.",
    ctaTitle: "Siapkan Bahan. Lancarkan Produksi.",
    ctaDescription: "Ubah prediksi permintaan menjadi keputusan produksi dan restock yang lebih tepat bersama ARUNA.",
    cta: "OPTIMALKAN PRODUKSI ANDA",
    slides: [
      ["Kelola Produksi Jus", "Lebih Cerdas", "Prediksi permintaan, siapkan bahan baku, dan rencanakan produksi dengan lebih tepat.", "Ilustrasi dashboard penjualan dan stok"],
      ["Prediksi Permintaan Jus", "Lebih Awal", "ARUNA mempelajari pola penjualan untuk memperkirakan jumlah jus yang akan dibutuhkan dalam beberapa hari ke depan. Jadi, produksi tidak lagi hanya bergantung pada perkiraan.", "Ilustrasi prediksi permintaan"],
      ["Ketahui Kebutuhan", "Bahan Baku Lebih Tepat", "Prediksi permintaan diterjemahkan menjadi kebutuhan bahan baku seperti buah, susu, gula, dan bahan lainnya. Siapkan yang dibutuhkan, sesuai jumlahnya.", "Ilustrasi kebutuhan bahan baku"],
      ["Kenali Risiko", "Kekurangan Stok", "ARUNA membandingkan kebutuhan produksi dengan stok yang tersedia untuk mendeteksi bahan yang berisiko habis lebih awal. Antisipasi sebelum produksi terganggu.", "Ilustrasi risiko stok"],
      ["Tentukan Waktu dan", "Jumlah Restock", "Dapatkan rekomendasi bahan apa yang perlu dibeli, berapa jumlahnya, dan kapan waktu terbaik untuk restock. Lebih siap menghadapi permintaan, tanpa menyimpan stok berlebihan.", "Ilustrasi perencanaan pengadaan"],
    ],
    steps: [
      ["Data Penjualan Masuk", "Transaksi jus tercatat sebagai dasar analisis permintaan."],
      ["Prediksi Permintaan", "ARUNA memperkirakan jumlah setiap menu jus yang akan terjual."],
      ["Hitung Kebutuhan Bahan", "Prediksi penjualan diterjemahkan menjadi kebutuhan setiap bahan baku."],
      ["Deteksi Risiko Stok", "Kebutuhan dibandingkan dengan stok yang tersedia untuk menemukan potensi kekurangan."],
      ["Rekomendasi Restock", "ARUNA menentukan bahan, jumlah, dan waktu pembelian yang disarankan."],
      ["Rencana Produksi", "Owner meninjau rekomendasi dan menentukan rencana produksi berikutnya."],
    ],
    cards: [
      ["Prediksi Permintaan", "Perkirakan jumlah menu jus yang dibutuhkan untuk beberapa hari ke depan."],
      ["Kebutuhan Bahan Baku", "Ketahui berapa banyak buah dan bahan lain yang diperlukan untuk memenuhi permintaan."],
      ["Risiko Kekurangan Stok", "Temukan bahan yang berpotensi tidak cukup sebelum mengganggu produksi."],
      ["Rekomendasi Jumlah", "Sesuaikan jumlah pembelian dengan kebutuhan produksi dan stok yang tersedia."],
      ["Waktu Restock", "Ketahui kapan bahan perlu dibeli agar tersedia saat dibutuhkan."],
    ],
  },
};
const images = ["overview", "forecast", "forecast", "risk", "procurement"];
const container = "mx-auto w-full max-w-[1240px] px-6 sm:px-10 lg:px-16";
const ctaClass = "inline-flex min-h-12 items-center justify-center rounded-full bg-accent px-7 text-sm font-bold tracking-wide text-ink shadow-md transition hover:brightness-110";

export function LandingPage() {
  const { locale, toggleLocale } = useInventoryLanguage();
  const copy = content[locale];
  const [activeSlide, setActiveSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isNavbarSolid, setIsNavbarSolid] = useState(false);
  const slide = copy.slides[activeSlide];
  const move = useCallback((direction: number) => {
    setActiveSlide((current) => (current + direction + images.length) % images.length);
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (isPaused || reducedMotion) return;
    const timeout = window.setTimeout(() => move(1), SLIDE_DURATION_MS);
    return () => window.clearTimeout(timeout);
  }, [activeSlide, isPaused, reducedMotion, move]);
  useEffect(() => {
    const update = () => setIsNavbarSolid(shouldUseSolidLandingNavbar(window.scrollY));
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  const logo = <><Image src="/landing/inventory-logo.png" alt="" width={114} height={64} className="h-9 w-16 object-contain" /><span className="text-lg font-semibold sm:text-xl">Aruna AI</span></>;
  return (
    <main className={`${theme.theme} overflow-x-hidden bg-primary text-white`}>
      <nav aria-label={copy.navigation} data-scroll-state={isNavbarSolid ? "solid" : "transparent"}
        className={`fixed inset-x-0 top-0 z-50 flex h-20 items-center transition-colors ${isNavbarSolid ? "border-b border-white/15 bg-primary-dark/95 shadow-lg backdrop-blur-xl" : "bg-transparent"}`}>
        <div className={`${container} flex items-center justify-between gap-4`}>
          <Link href="/" aria-label="Aruna AI" className="flex shrink-0 items-center gap-2">{logo}</Link>
          <div className="flex items-center gap-3 lg:gap-7">
            <div className="hidden items-center gap-7 text-sm text-white/90 md:flex">
              <a href="#beranda" className="hover:text-accent">{copy.home}</a>
              <a href="#cara-kerja" className="hover:text-accent">{copy.how}</a>
              <a href="#fitur" className="hover:text-accent">{copy.features}</a>
            </div>
            <button type="button" onClick={toggleLocale} aria-label={copy.switchLanguage} className="flex min-h-11 items-center gap-1.5 rounded-full border border-white/40 px-3 text-xs font-semibold hover:bg-white/10">
              <Languages size={16} aria-hidden="true" />{locale === "en" ? "ID" : "EN"}
            </button>
            <Link href={LANDING_APP_HREF} className={`${ctaClass} hidden sm:inline-flex`}>{copy.start}</Link>
          </div>
        </div>
      </nav>

      <section id="beranda" aria-roledescription="carousel" aria-label={copy.home} className="landing-grid relative scroll-mt-20 bg-[linear-gradient(155deg,var(--color-primary-dark),var(--color-primary))] pb-12 pt-28 sm:pt-32">
        <div className={`${container} relative grid min-h-[470px] items-center gap-8 pb-10 md:grid-cols-[1.2fr_1fr] lg:min-h-[510px] lg:gap-16`}>
          <div key={`copy-${activeSlide}`} className="landing-slide-copy motion-reduce:animate-none">
            <h1 className="max-w-[580px] text-4xl font-bold leading-[1.13] tracking-tight sm:text-5xl lg:text-[58px]">
              <span className={activeSlide === 0 ? "text-[var(--color-caution)]" : "text-white"}>{slide[0]}</span><br />
              <span className={activeSlide === 0 ? "text-white" : "text-[var(--color-caution)]"}>{slide[1]}</span>
            </h1>
            <p className="mt-5 max-w-[520px] text-sm leading-relaxed text-white/90 sm:text-base">{slide[2]}</p>
            <Link href={LANDING_APP_HREF} className={`${ctaClass} mt-7 min-w-52 uppercase`}>{copy.explore}</Link>
          </div>
          <div key={`${activeSlide}-${images[activeSlide]}`} className="landing-slide-image relative mx-auto aspect-square w-full max-w-[340px] motion-reduce:animate-none lg:max-w-[390px]">
            <Image src={`/landing/inventory-${images[activeSlide]}.png`} alt={slide[3]} fill priority={activeSlide === 0} sizes="(max-width: 767px) 80vw, 390px" className="object-contain drop-shadow-[0_0_20px_rgb(255_255_255/20%)]" />
          </div>
        </div>
        <div className="relative flex items-center justify-center gap-1 sm:gap-3">
          <button type="button" onClick={() => move(-1)} aria-label={copy.previous} className="grid size-10 place-items-center rounded-full hover:bg-white/10"><ChevronLeft size={20} /></button>
          <div className="flex items-center" role="group" aria-label={locale === "en" ? "Choose a slide" : "Pilih slide"}>
            {images.map((name, index) => <button type="button" key={`${name}-${index}`} onClick={() => setActiveSlide(index)} aria-label={`${copy.slide} ${index + 1}`} aria-current={index === activeSlide ? "true" : undefined} className="grid size-10 shrink-0 place-items-center rounded-full hover:bg-white/10">
              <span aria-hidden="true" className={`block rounded-full transition-colors ${index === activeSlide ? "size-3 bg-accent" : "size-2.5 bg-white/40"}`} />
            </button>)}
          </div>
          <button type="button" onClick={() => move(1)} aria-label={copy.next} className="grid size-10 place-items-center rounded-full hover:bg-white/10"><ChevronRight size={20} /></button>
          {!reducedMotion && <button type="button" onClick={() => setIsPaused((paused) => !paused)} aria-label={isPaused ? copy.resume : copy.pause} className="grid size-10 place-items-center rounded-full hover:bg-white/10">{isPaused ? <Play size={16} /> : <Pause size={16} />}</button>}
        </div>
      </section>

      <section id="cara-kerja" className="scroll-mt-20 bg-primary py-16 sm:py-20">
        <div className={container}>
          <p className="text-center text-sm font-semibold uppercase tracking-[.18em] text-white/80">{copy.how}</p>
          <h2 className="mt-8 text-3xl font-extrabold tracking-tight text-accent sm:text-4xl">{copy.howTitle}</h2>
          <p className="mt-3 max-w-[950px] text-sm leading-relaxed text-white/90 sm:text-base">{copy.howDescription}</p>
          <ol className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {copy.steps.map(([title, description], index) => <li key={title} className="rounded-2xl bg-white px-4 py-6 text-center text-ink shadow-sm">
              <span className="relative mx-auto grid size-[63px] place-items-center"><Image src="/landing/inventory-step.svg" alt="" width={63} height={63} /><span className="absolute text-xl font-bold text-white">{index + 1}</span></span>
              <h3 className="mt-4 text-sm font-bold">{title}</h3><p className="mt-3 text-xs leading-relaxed text-muted">{description}</p>
            </li>)}
          </ol>
        </div>
      </section>

      <section id="fitur" className="landing-honeycomb scroll-mt-20 bg-secondary-soft py-16 text-primary sm:py-20">
        <div className={container}>
          <p className="text-center text-sm font-semibold uppercase tracking-[.18em] text-primary-dark">{copy.features}</p>
          <h2 className="mt-8 text-3xl font-extrabold tracking-tight sm:text-4xl">{copy.featureTitle}</h2>
          <p className="mt-3 max-w-[950px] text-sm leading-relaxed sm:text-base">{copy.featureDescription}</p>
          <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {copy.cards.map(([title, description], index) => <article key={title} className="rounded-2xl bg-white/75 px-5 py-6 text-center text-ink shadow-sm">
              <span className="relative mx-auto grid size-[75.6px] place-items-center"><Image src="/landing/inventory-feature.svg" alt="" width={75.6} height={75.6} /><span className="absolute text-2xl font-bold text-white">{index + 1}</span></span>
              <h3 className="mt-4 text-base font-bold">{title}</h3><p className="mt-3 text-sm leading-relaxed text-muted">{description}</p>
            </article>)}
          </div>
        </div>
      </section>

      <section className="bg-accent py-16 text-center text-ink sm:py-20">
        <div className={container}><h2 className="text-3xl font-extrabold sm:text-4xl">{copy.ctaTitle}</h2>
          <p className="mx-auto mt-4 max-w-[820px] text-sm leading-relaxed sm:text-base">{copy.ctaDescription}</p>
          <Link href={LANDING_APP_HREF} className="mt-7 inline-flex min-h-14 items-center justify-center rounded-full bg-primary-dark px-8 text-sm font-semibold uppercase tracking-wider text-white shadow-md transition hover:bg-primary">{copy.cta}</Link>
        </div>
      </section>
      <footer className="bg-primary-dark py-8"><div className={container}><Link href="/" aria-label="Aruna AI" className="inline-flex items-center gap-2">{logo}</Link></div></footer>
    </main>
  );
}
