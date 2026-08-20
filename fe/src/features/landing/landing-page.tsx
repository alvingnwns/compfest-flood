"use client";

import Image from "next/image";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const SLIDE_DURATION_MS = 5500;

const slides = [
  { title: <>Siapkan Bisnis Anda <span className="text-white">Hadapi Banjir</span></>, description: "Kenali risiko lebih awal, ambil langkah lebih cepat.", image: "/landing/asset-1.png", alt: "Tim bisnis merencanakan ketahanan rantai pasok" },
  { title: <>Memprediksi Risiko Banjir <span className="text-accent">Lebih Awal</span></>, description: "ResiliChain menggunakan model Random Forest Classifier untuk membantu bisnis mengantisipasi gangguan dan mempersiapkan langkah lebih awal.", image: "/landing/asset-3.png", alt: "Visualisasi banjir perkotaan" },
  { title: <>Memetakan <span className="text-accent">Dampak Banjir</span> <span className="text-white">pada Jalan</span></>, description: "Identifikasi jalan yang berpotensi terdampak banjir dan pahami pengaruhnya terhadap akses serta distribusi barang.", image: "/landing/asset-5.png", alt: "Visualisasi jaringan jalan terdampak banjir" },
  { title: <>Menentukan Strategi saat <span className="text-accent">Terjadi Banjir</span></>, description: "Analisis kondisi jalan untuk menentukan rute alternatif dan prioritas distribusi agar bisnis dapat mengurangi dampak gangguan.", image: "/landing/asset-7.png", alt: "Visualisasi strategi dan rute pemulihan" },
];

const steps = [
  ["Data Masuk", "Data cuaca, banjir, jaringan jalan, dan informasi bisnis dikumpulkan sebagai dasar analisis."],
  ["Prediksi Risiko Banjir", "AI Random Forest memprediksi tingkat risiko paparan banjir pada koridor jalan."],
  ["Analisis Jaringan Jalan", "Sistem memetakan jalan yang berpotensi terdampak dan melihat perubahan akses akibat banjir."],
  ["Dampak Distribusi", "Menganalisis dampak gangguan jalan terhadap perjalanan dan distribusi barang."],
  ["Rekomendasi Rute", "Sistem mencari alternatif rute dan menentukan prioritas berdasarkan kondisi jaringan."],
  ["Rencana Pemulihan", "Hasil analisis dirangkum menjadi langkah yang membantu bisnis mengurangi dampak gangguan."],
];

const features = [
  ["Prediksi Risiko Banjir", "Memprediksi tingkat paparan banjir pada koridor jalan menggunakan AI."],
  ["Peta Dampak Jalan", "Menampilkan lokasi dan tingkat dampak banjir pada jaringan jalan."],
  ["Analisis Distribusi", "Menilai bagaimana gangguan jalan memengaruhi pergerakan barang."],
  ["Rute Alternatif", "Menentukan rute lain untuk membantu distribusi tetap berjalan."],
  ["Prioritas Pemulihan", "Membantu menentukan prioritas dan langkah setelah terjadi gangguan."],
];

export function LandingPage() {
  const [activeSlide, setActiveSlide] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isNavbarSolid, setIsNavbarSolid] = useState(false);
  const slide = slides[activeSlide];
  const move = useCallback((direction: number) => {
    setActiveSlide((current) => (current + direction + slides.length) % slides.length);
  }, []);

  useEffect(() => {
    if (isPaused) return;
    const timeout = window.setTimeout(() => move(1), SLIDE_DURATION_MS);
    return () => window.clearTimeout(timeout);
  }, [activeSlide, isPaused, move]);

  useEffect(() => {
    const updateNavbar = () => setIsNavbarSolid(window.scrollY > 56);
    updateNavbar();
    window.addEventListener("scroll", updateNavbar, { passive: true });
    return () => window.removeEventListener("scroll", updateNavbar);
  }, []);

  return <main className="overflow-x-hidden bg-primary text-white">
    <nav aria-label="Navigasi landing page" className={`fixed inset-x-0 top-0 z-50 flex h-[96px] w-full items-center transition-[background-color,border-color,box-shadow,backdrop-filter] duration-300 ${isNavbarSolid ? "border-b border-white/10 bg-primary/90 shadow-[0_8px_24px_rgb(41_64_91/18%)] backdrop-blur-md" : "border-b border-transparent bg-transparent shadow-none"}`}>
      <div className="mx-auto flex w-full max-w-[1480px] items-center justify-between px-6 lg:px-12">
        <Link href="/" className="flex items-center gap-3" aria-label="ResiliChain AI beranda"><span className="h-[54px] w-[54px] rounded-[14px] bg-secondary-soft" aria-hidden="true" /><span className="text-[22px] font-semibold text-[#eaeced] md:text-[30px]">ResiliChain AI</span></Link>
        <div className="hidden items-center gap-10 text-[16px] text-[#eaeced] md:flex"><a href="#beranda" className="transition hover:text-accent">Beranda</a><a href="#cara-kerja" className="transition hover:text-accent">Cara Kerja</a><a href="#fitur" className="transition hover:text-accent">Fitur</a><Link href="/scenario" className="rounded-full bg-[linear-gradient(180deg,#eba92d,#856019)] px-7 py-3 font-bold text-white shadow-lg transition hover:brightness-110">Start Now!</Link></div>
        <Link href="/scenario" className="rounded-full bg-accent px-5 py-2.5 text-sm font-bold text-primary-dark md:hidden">Mulai</Link>
      </div>
    </nav>

    <section id="beranda" className="landing-grid relative min-h-[840px] scroll-mt-[96px] bg-primary pt-[96px]">
      <h1 className="sr-only">ResiliChain AI</h1>
      <div className="relative mx-auto grid min-h-[620px] w-full max-w-[1480px] items-center gap-10 px-6 pb-20 pt-8 lg:grid-cols-[minmax(0,620px)_minmax(360px,560px)] lg:justify-between lg:px-12">
        <div key={`copy-${activeSlide}`} aria-live="polite" className="landing-slide-copy relative z-10"><p className="max-w-[620px] text-[46px] font-bold leading-[1.06] text-[#ffc558] [text-shadow:0_0_19px_rgb(0_0_0/25%)] md:text-[64px] lg:text-[76px]">{slide.title}</p><p className="mt-7 max-w-[600px] text-[17px] leading-relaxed text-[#eaeced] md:text-[21px]">{slide.description}</p><Link href="/scenario" className="mt-9 inline-flex h-[72px] min-w-[290px] items-center justify-center rounded-full bg-[linear-gradient(90deg,#eba92d,#856019)] px-8 text-[18px] font-semibold text-white shadow-xl transition hover:brightness-110">EXPLORE NOW!</Link></div>
        <div key={`image-${activeSlide}`} className="landing-slide-image relative mx-auto aspect-square w-full max-w-[520px]"><Image src={slide.image} alt={slide.alt} fill priority={activeSlide === 0} sizes="(max-width: 1024px) 90vw, 520px" className="object-contain drop-shadow-[0_12px_28px_rgb(255_255_255/14%)]" /></div>
      </div>
      <div className="absolute bottom-9 left-1/2 z-20 flex -translate-x-1/2 items-center gap-4">
        <button type="button" onClick={() => move(-1)} aria-label="Slide sebelumnya" className="grid size-9 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"><ChevronLeft /></button>
        <div className="w-[118px]">
          <div className="flex justify-center gap-3">{slides.map((item, index) => <button key={item.image} type="button" onClick={() => setActiveSlide(index)} aria-label={`Buka slide ${index + 1}`} aria-current={index === activeSlide} className={`size-2.5 rounded-full transition ${index === activeSlide ? "scale-125 bg-white" : "bg-white/55 hover:bg-white"}`} />)}</div>
          <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/20" aria-hidden="true"><span key={activeSlide} className={`landing-slide-progress block h-full rounded-full bg-accent ${isPaused ? "[animation-play-state:paused]" : ""}`} /></div>
        </div>
        <button type="button" onClick={() => move(1)} aria-label="Slide berikutnya" className="grid size-9 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"><ChevronRight /></button>
        <button type="button" onClick={() => setIsPaused((paused) => !paused)} aria-label={isPaused ? "Lanjutkan carousel otomatis" : "Jeda carousel otomatis"} title={isPaused ? "Putar otomatis" : "Jeda autoplay"} className="grid size-9 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white">{isPaused ? <Play className="size-4" fill="currentColor" /> : <Pause className="size-4" fill="currentColor" />}</button>
      </div>
    </section>

    <section id="cara-kerja" className="scroll-mt-[96px] bg-primary px-6 py-20"><div className="mx-auto max-w-[1480px]">
      <p className="text-center text-[18px] font-semibold text-[#d9d9d9]">CARA KERJA</p><h2 className="mt-6 text-[38px] font-extrabold text-[#ffc558] md:text-[54px]">Dari Data Menjadi Keputusan</h2><p className="mt-3 max-w-[1250px] text-[18px] leading-relaxed text-[#eaeced] md:text-[23px]">ResiliChain mengolah data banjir, jaringan jalan, dan distribusi untuk menghasilkan rekomendasi yang dapat ditindaklanjuti.</p>
      <ol className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">{steps.map(([title, description], index) => <li key={title} className="min-h-[330px] rounded-[20px] bg-white px-5 py-8 text-center text-black"><span className="mx-auto grid size-[58px] place-items-center rounded-full bg-primary text-[28px] font-bold text-white shadow-lg">{index + 1}</span><h3 className="mt-5 text-[18px] font-bold leading-tight">{title}</h3><p className="mt-4 text-[14px] font-medium leading-relaxed text-[#5a5a5a]">{description}</p></li>)}</ol>
    </div></section>

    <section id="fitur" className="landing-honeycomb scroll-mt-[96px] bg-secondary-soft px-6 py-20 text-primary"><div className="mx-auto max-w-[1480px]">
      <p className="text-center text-[18px] font-semibold text-primary-dark">FITUR</p><h2 className="mt-6 text-[38px] font-extrabold md:text-[54px]">Solusi Cerdas untuk Bisnis</h2><p className="mt-3 max-w-[1280px] text-[18px] leading-relaxed md:text-[23px]">Dari prediksi banjir hingga rute alternatif, ResiliChain membantu bisnis menghadapi gangguan dengan lebih siap.</p>
      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">{features.map(([title, description], index) => <article key={title} className="min-h-[350px] rounded-[20px] bg-white/75 px-6 py-9 text-center text-black shadow-sm"><span className="mx-auto grid size-[68px] place-items-center rounded-full bg-accent text-[30px] font-bold text-white shadow-lg">{index + 1}</span><h3 className="mt-6 text-[20px] font-bold leading-tight">{title}</h3><p className="mt-5 text-[15px] font-semibold leading-relaxed text-[#5a5a5a]">{description}</p></article>)}</div>
    </div></section>

    <section className="bg-[linear-gradient(180deg,#eba92d,#a16d12)] px-6 py-20 text-center"><h2 className="text-[36px] font-extrabold md:text-[50px]">Bangun Ketahanan Bisnis Anda</h2><p className="mx-auto mt-5 max-w-[900px] text-[18px] leading-relaxed">Uji skenario banjir, pahami dampaknya, dan siapkan keputusan pemulihan sebelum gangguan terjadi.</p><Link href="/scenario" className="mt-9 inline-flex min-h-[72px] min-w-[min(100%,520px)] items-center justify-center rounded-full bg-primary-dark px-10 text-[17px] font-semibold text-white shadow-xl transition hover:bg-primary">CREATE YOUR SCENARIO HERE</Link></section>
    <footer className="flex min-h-[150px] items-center bg-primary-dark px-6"><div className="mx-auto flex w-full max-w-[1480px] items-center gap-3"><span className="size-[50px] rounded-[12px] bg-secondary-soft" aria-hidden="true" /><span className="text-[24px] font-semibold">ResiliChain AI</span></div></footer>
  </main>;
}
