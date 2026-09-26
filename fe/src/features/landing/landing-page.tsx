"use client";

import Image from "next/image";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Languages, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useInventoryLanguage } from "@/components/providers/inventory-language-provider";

const SLIDE_DURATION_MS = 5500;
export const LANDING_NAVBAR_SOLID_Y = 48;
export const LANDING_APP_HREF = "/ringkasan";
export function shouldUseSolidLandingNavbar(scrollY: number): boolean {
  return scrollY >= LANDING_NAVBAR_SOLID_Y;
}

const content = {
  en: {
    home: "Home", how: "How it works", features: "Features", start: "Start now", explore: "Explore now",
    navigation: "Landing navigation", switchLanguage: "Switch to Indonesian",
    previous: "Previous slide", next: "Next slide", pause: "Pause autoplay", resume: "Resume autoplay", slide: "Go to slide",
    howTitle: "From data to decisions",
    howDescription: "ARUNA turns sales and stock data into actionable recommendations for your business.",
    featureTitle: "Smarter solutions for your business",
    featureDescription: "From tracking sales to planning replenishment, keep your inventory ready for what comes next.",
    ctaTitle: "Ready stock. Smoother business.",
    ctaDescription: "Make informed decisions with demand forecasts and replenishment recommendations from ARUNA.",
    cta: "Optimize your inventory",
    slides: [
      ["Manage your business", "Smarter", "Track sales, manage inventory, and plan procurement with ease.", "Sales and inventory dashboard illustration"],
      ["Forecast stock needs", "Ahead of time", "Forecast demand for the next three days using sales history, then translate it into ingredient needs. When history is insufficient, ARUNA clearly identifies its fallback estimates.", "Demand forecast illustration"],
      ["Spot stockout risks", "Before they happen", "Compare available stock with projected needs to identify ingredients that require attention.", "Inventory risk illustration"],
      ["Plan your purchases", "Quantity and timing", "Review replenishment recommendations based on stock needs, supplier lead times, and purchasing constraints.", "Procurement planning illustration"],
    ],
    steps: [
      ["Collect data", "Sales and inventory records form the foundation for analysis."],
      ["Forecast demand", "Estimate demand for the next three days from sales history."],
      ["Calculate needs", "Convert product forecasts into required ingredient quantities."],
      ["Detect stock risks", "Compare projected needs with available inventory."],
      ["Recommend restocking", "Identify what to buy, how much, and when it is needed."],
      ["Review the plan", "Review and approve recommendations. Record stock only when goods arrive."],
    ],
    cards: [
      ["Forecast needs", "Estimate ingredient requirements for the next three days."],
      ["Manage stock", "Identify ingredients that need attention before stock runs out."],
      ["Recommended quantities", "Align purchases with projected demand and current inventory."],
      ["Purchase timing", "Plan replenishment around supplier delivery lead times."],
      ["Review plans", "Review and approve recommendations to suit your business."],
    ],
  },
  id: {
    home: "Beranda", how: "Cara kerja", features: "Fitur", start: "Mulai sekarang", explore: "Jelajahi sekarang",
    navigation: "Navigasi landing page", switchLanguage: "Ganti ke bahasa Inggris",
    previous: "Slide sebelumnya", next: "Slide berikutnya", pause: "Jeda carousel otomatis", resume: "Lanjutkan carousel otomatis", slide: "Buka slide",
    howTitle: "Dari Data Menjadi Keputusan",
    howDescription: "ARUNA mengolah data penjualan dan stok menjadi rekomendasi yang dapat ditindaklanjuti oleh bisnis.",
    featureTitle: "Solusi Cerdas untuk Bisnis",
    featureDescription: "Dari pemantauan penjualan hingga perencanaan restock, kelola stok dengan lebih siap.",
    ctaTitle: "Siapkan Stok, Lancarkan Bisnis",
    ctaDescription: "Ambil keputusan lebih tepat dengan prediksi permintaan dan rekomendasi restock dari ARUNA.",
    cta: "Optimalkan stok bisnis Anda",
    slides: [
      ["Kelola Bisnis Anda", "Lebih Cerdas", "Pantau penjualan, kelola stok, dan rencanakan pengadaan dengan mudah.", "Ilustrasi dashboard penjualan dan stok"],
      ["Prediksi Kebutuhan Stok", "Lebih Awal", "Prediksi permintaan tiga hari ke depan dari riwayat penjualan, lalu terjemahkan menjadi kebutuhan bahan. Jika riwayat belum cukup, ARUNA menandai estimasi fallback secara jelas.", "Ilustrasi prediksi permintaan"],
      ["Kenali Risiko Kehabisan Stok", "Sebelum Terjadi", "Bandingkan stok tersedia dengan prediksi kebutuhan untuk mengidentifikasi bahan yang perlu segera ditindaklanjuti.", "Ilustrasi risiko stok"],
      ["Rencanakan Pembelian", "Jumlah dan Waktunya", "Tinjau rekomendasi restock berdasarkan kebutuhan bahan, durasi pengiriman pemasok, dan batasan pembelian.", "Ilustrasi perencanaan pengadaan"],
    ],
    steps: [
      ["Data Masuk", "Data penjualan dan jumlah stok dikumpulkan sebagai dasar analisis."],
      ["Prediksi Permintaan", "Perkirakan permintaan untuk tiga hari ke depan dari riwayat penjualan."],
      ["Analisis Kebutuhan", "Hasil prediksi diterjemahkan menjadi jumlah bahan yang dibutuhkan."],
      ["Deteksi Risiko Stok", "Kebutuhan bahan dibandingkan dengan stok yang tersedia."],
      ["Rekomendasi Restock", "Tentukan bahan yang perlu dibeli, jumlah, dan waktunya."],
      ["Rencana Optimasi", "Tinjau dan setujui rekomendasi. Catat stok saat barang diterima."],
    ],
    cards: [
      ["Prediksi Kebutuhan", "Perkirakan kebutuhan bahan untuk tiga hari ke depan."],
      ["Kelola Stok", "Kenali bahan yang perlu ditambah sebelum stok habis."],
      ["Rekomendasi Jumlah", "Sesuaikan pembelian dengan kebutuhan dan stok tersedia."],
      ["Waktu Pembelian", "Rencanakan restock dengan mempertimbangkan durasi pengiriman."],
      ["Tinjau Rencana", "Periksa dan setujui rekomendasi sesuai kebutuhan bisnis."],
    ],
  },
};
const images = ["overview", "forecast", "risk", "procurement"];
const container = "mx-auto w-full max-w-[1240px] px-6 sm:px-10 lg:px-16";
const ctaClass = "inline-flex min-h-12 items-center justify-center rounded-full bg-[linear-gradient(110deg,#eba92d,#856019)] px-7 text-sm font-bold tracking-wide text-white shadow-md transition hover:brightness-110";

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
    <main className="overflow-x-hidden bg-primary text-white">
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

      <section id="beranda" aria-roledescription="carousel" aria-label={copy.home} className="landing-grid relative scroll-mt-20 bg-[linear-gradient(155deg,#39597e,#789ab8)] pb-12 pt-28 sm:pt-32">
        <div className={`${container} relative grid min-h-[470px] items-center gap-8 pb-10 md:grid-cols-[1.2fr_1fr] lg:min-h-[510px] lg:gap-16`}>
          <div key={`copy-${activeSlide}`} className="landing-slide-copy motion-reduce:animate-none">
            <h1 className="max-w-[580px] text-4xl font-bold leading-[1.13] tracking-tight sm:text-5xl lg:text-[58px]">
              <span className={activeSlide === 0 ? "text-[#ffc558]" : "text-white"}>{slide[0]}</span><br />
              <span className={activeSlide === 0 ? "text-white" : "text-[#ffc558]"}>{slide[1]}</span>
            </h1>
            <p className="mt-5 max-w-[520px] text-sm leading-relaxed text-white/90 sm:text-base">{slide[2]}</p>
            <Link href={LANDING_APP_HREF} className={`${ctaClass} mt-7 min-w-52 uppercase`}>{copy.explore}</Link>
          </div>
          <div key={images[activeSlide]} className="landing-slide-image relative mx-auto aspect-square w-full max-w-[340px] motion-reduce:animate-none lg:max-w-[390px]">
            <Image src={`/landing/inventory-${images[activeSlide]}.png`} alt={slide[3]} fill priority={activeSlide === 0} sizes="(max-width: 767px) 80vw, 390px" className="object-contain drop-shadow-[0_0_20px_rgb(255_255_255/20%)]" />
          </div>
        </div>
        <div className="relative flex items-center justify-center gap-3">
          <button type="button" onClick={() => move(-1)} aria-label={copy.previous} className="grid size-10 place-items-center rounded-full hover:bg-white/10"><ChevronLeft size={20} /></button>
          <div className="relative h-[14px] w-[150px]">
            <Image src="/landing/inventory-dots.svg" alt="" width={149.76} height={13.44} aria-hidden="true" />
            <div className="absolute inset-0 flex items-center justify-between">
              {images.map((name, index) => <button type="button" key={name} onClick={() => setActiveSlide(index)} aria-label={`${copy.slide} ${index + 1}`} aria-current={index === activeSlide ? "true" : undefined} className={`relative -my-3 grid h-10 w-5 place-items-center rounded-full ${index === activeSlide ? "after:size-3 after:rounded-full after:bg-white after:ring-2 after:ring-primary" : ""}`} />)}
            </div>
          </div>
          <button type="button" onClick={() => move(1)} aria-label={copy.next} className="grid size-10 place-items-center rounded-full hover:bg-white/10"><ChevronRight size={20} /></button>
          {!reducedMotion && <button type="button" onClick={() => setIsPaused((paused) => !paused)} aria-label={isPaused ? copy.resume : copy.pause} className="grid size-10 place-items-center rounded-full hover:bg-white/10">{isPaused ? <Play size={16} /> : <Pause size={16} />}</button>}
        </div>
      </section>

      <section id="cara-kerja" className="scroll-mt-20 bg-primary py-16 sm:py-20">
        <div className={container}>
          <p className="text-center text-sm font-semibold uppercase tracking-[.18em] text-white/80">{copy.how}</p>
          <h2 className="mt-8 text-3xl font-extrabold tracking-tight text-[#ffc558] sm:text-4xl">{copy.howTitle}</h2>
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

      <section className="bg-[linear-gradient(180deg,#eba92d,#956b1b)] py-16 text-center sm:py-20">
        <div className={container}><h2 className="text-3xl font-extrabold sm:text-4xl">{copy.ctaTitle}</h2>
          <p className="mx-auto mt-4 max-w-[820px] text-sm leading-relaxed sm:text-base">{copy.ctaDescription}</p>
          <Link href={LANDING_APP_HREF} className="mt-7 inline-flex min-h-14 items-center justify-center rounded-full bg-primary-dark px-8 text-sm font-semibold uppercase tracking-wider text-white shadow-md transition hover:bg-primary">{copy.cta}</Link>
        </div>
      </section>
      <footer className="bg-primary-dark py-8"><div className={container}><Link href="/" aria-label="Aruna AI" className="inline-flex items-center gap-2">{logo}</Link></div></footer>
    </main>
  );
}
