"use client";

import Image from "next/image";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const SLIDE_DURATION_MS = 5500;

const slides = [
  {
    title: (
      <>
        <span className="text-[#ffc558]">Siapkan<br />Bisnis Anda</span>{" "}
        <span className="text-white">Hadapi Banjir</span>
      </>
    ),
    description: "Kenali risiko lebih awal, ambil langkah lebih cepat.",
    image: "/landing/asset-1.png",
    alt: "Tim bisnis merencanakan ketahanan rantai pasok",
    hasCta: true,
  },
  {
    title: (
      <>
        <span className="text-white">Memprediksi<br />Resiko Banjir</span>{" "}
        <span className="text-[#ffc558]">Lebih Awal</span>
      </>
    ),
    description:
      "ARUNA menggunakan model Random Forest Classifier untuk membantu bisnis mengantisipasi gangguan dan mempersiapkan langkah lebih awal.",
    image: "/landing/asset-3.png",
    alt: "Visualisasi prediksi risiko banjir perkotaan",
    hasCta: false,
  },
  {
    title: (
      <>
        <span className="text-white">Memetakan</span><br />
        <span className="text-[#ffc558]">Dampak Banjir</span>{" "}
        <span className="text-white">pada Jalan</span>
      </>
    ),
    description:
      "Identifikasi jalan yang berpotensi terdampak banjir dan pahami pengaruhnya terhadap akses serta distribusi barang.",
    image: "/landing/asset-5.png",
    alt: "Visualisasi jaringan jalan terdampak banjir",
    hasCta: false,
  },
  {
    title: (
      <>
        <span className="text-white">Menentukan<br />Strategi saat</span>{" "}
        <span className="text-[#ffc558]">Terjadi Banjir</span>
      </>
    ),
    description:
      "Analisis kondisi jalan untuk menentukan rute alternatif dan prioritas distribusi agar bisnis dapat mengurangi dampak gangguan.",
    image: "/landing/asset-7.png",
    alt: "Visualisasi penentuan strategi pemulihan",
    hasCta: false,
  },
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

  return (
    <main className="overflow-x-hidden bg-primary text-white">
      <nav
        aria-label="Navigasi landing page"
        className={`fixed inset-x-0 top-0 z-50 flex h-[90px] w-full items-center transition-[background-color,border-color,box-shadow,backdrop-filter] duration-300 ${isNavbarSolid
          ? "border-b border-white/10 bg-primary/95 shadow-[0_8px_24px_rgb(41_64_91/18%)] backdrop-blur-md"
          : "border-b border-transparent bg-transparent shadow-none"
          }`}
      >
        <div className="mx-auto flex w-full max-w-[1240px] items-center justify-between px-8 md:px-14 lg:px-16">
          <Link href="/" className="flex items-center gap-3" aria-label="ARUNA beranda">
            <Image
              src="/logo-aruna.png"
              alt="ARUNA Logo"
              width={56}
              height={32}
              priority
              className="h-9 w-auto object-contain drop-shadow-sm"
            />
            <span className="text-[22px] font-bold tracking-wide text-[#eaeced] md:text-[28px]">ARUNA</span>
          </Link>
          <div className="hidden items-center gap-8 text-[15px] text-[#eaeced] md:flex">
            <a href="#beranda" className="transition hover:text-accent">
              Beranda
            </a>
            <a href="#cara-kerja" className="transition hover:text-accent">
              Cara Kerja
            </a>
            <a href="#fitur" className="transition hover:text-accent">
              Fitur
            </a>
            <Link
              href="/scenario"
              className="rounded-full bg-[linear-gradient(180deg,#eba92d,#856019)] px-6 py-2.5 font-bold text-white shadow-md transition hover:brightness-110"
            >
              Start Now!
            </Link>
          </div>
          <Link
            href="/scenario"
            className="rounded-full bg-accent px-4 py-2 text-xs font-bold text-primary-dark md:hidden"
          >
            Mulai
          </Link>
        </div>
      </nav>

      <section id="beranda" className="landing-grid relative min-h-[780px] scroll-mt-[90px] bg-primary pt-[90px]">
        <h1 className="sr-only">ARUNA</h1>
        <div className="relative mx-auto grid min-h-[580px] w-full max-w-[1240px] items-center gap-10 px-8 pb-20 pt-8 md:px-14 lg:grid-cols-[minmax(0,540px)_minmax(320px,460px)] lg:justify-between lg:px-16">
          <div key={`copy-${activeSlide}`} aria-live="polite" className="landing-slide-copy relative z-10">
            <div className="max-w-[540px] text-[38px] font-bold leading-[1.1] [text-shadow:0_0_19px_rgb(0_0_0/25%)] md:text-[52px] lg:text-[62px]">
              {slide.title}
            </div>
            <p className="mt-5 max-w-[500px] text-[15px] leading-relaxed text-[#eaeced] md:text-[18px]">
              {slide.description}
            </p>
            {slide.hasCta && (
              <Link
                href="/scenario"
                className="mt-8 inline-flex h-[64px] min-w-[240px] items-center justify-center rounded-full bg-[linear-gradient(90deg,#eba92d,#856019)] px-7 text-[16px] font-bold text-white shadow-lg transition hover:brightness-110 active:scale-95"
              >
                EXPLORE NOW!
              </Link>
            )}
          </div>
          <div
            key={`image-${activeSlide}`}
            className="landing-slide-image relative mx-auto aspect-square w-full max-w-[440px]"
          >
            <Image
              src={slide.image}
              alt={slide.alt}
              fill
              priority={activeSlide === 0}
              sizes="(max-width: 1024px) 85vw, 440px"
              className="object-contain drop-shadow-[0_12px_28px_rgb(255_255_255/14%)]"
            />
          </div>
        </div>
        <div className="absolute bottom-8 left-1/2 z-20 flex -translate-x-1/2 items-center gap-4">
          <button
            type="button"
            onClick={() => move(-1)}
            aria-label="Slide sebelumnya"
            className="grid size-8 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            <ChevronLeft className="size-5" />
          </button>
          <div className="w-[110px]">
            <div className="flex justify-center gap-2.5">
              {slides.map((item, index) => (
                <button
                  key={item.image}
                  type="button"
                  onClick={() => setActiveSlide(index)}
                  aria-label={`Buka slide ${index + 1}`}
                  aria-current={index === activeSlide}
                  className={`size-2.5 rounded-full transition ${index === activeSlide ? "scale-125 bg-white" : "bg-white/55 hover:bg-white"
                    }`}
                />
              ))}
            </div>
            <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-white/20" aria-hidden="true">
              <span
                key={activeSlide}
                className={`landing-slide-progress block h-full rounded-full bg-accent ${isPaused ? "[animation-play-state:paused]" : ""
                  }`}
              />
            </div>
          </div>
          <button
            type="button"
            onClick={() => move(1)}
            aria-label="Slide berikutnya"
            className="grid size-8 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            <ChevronRight className="size-5" />
          </button>
          <button
            type="button"
            onClick={() => setIsPaused((paused) => !paused)}
            aria-label={isPaused ? "Lanjutkan carousel otomatis" : "Jeda carousel otomatis"}
            title={isPaused ? "Putar otomatis" : "Jeda autoplay"}
            className="grid size-8 place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            {isPaused ? <Play className="size-3.5" fill="currentColor" /> : <Pause className="size-3.5" fill="currentColor" />}
          </button>
        </div>
      </section>

      <section id="cara-kerja" className="scroll-mt-[90px] bg-primary-dark px-8 py-24 md:px-14 lg:px-16">
        <div className="mx-auto max-w-[1240px]">
          <p className="text-center text-[18px] font-bold tracking-[0.18em] text-[#d9d9d9] md:text-[22px]">
            CARA KERJA
          </p>
          <h2 className="mt-4 text-[32px] font-extrabold text-[#ffc558] md:text-[46px]">
            Dari Data Menjadi Keputusan
          </h2>
          <p className="mt-3 max-w-[1050px] text-[15px] leading-relaxed text-[#eaeced] md:text-[19px]">
            ARUNA mengolah data banjir, jaringan jalan, dan distribusi untuk menghasilkan rekomendasi yang dapat ditindaklanjuti.
          </p>
          <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {steps.map(([title, description], index) => (
              <li
                key={title}
                className="flex min-h-[300px] flex-col rounded-[22px] bg-white px-4 py-6 text-center text-black shadow-md transition hover:-translate-y-1 hover:shadow-xl"
              >
                <span className="mx-auto grid size-[50px] place-items-center rounded-full bg-primary text-[22px] font-bold text-white shadow-md">
                  {index + 1}
                </span>
                <h3 className="mt-4 text-[16px] font-bold leading-tight">{title}</h3>
                <p className="mt-3 text-[12px] font-medium leading-relaxed text-[#5a5a5a]">{description}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="fitur" className="landing-honeycomb scroll-mt-[90px] bg-secondary-soft px-8 py-24 text-primary md:px-14 lg:px-16">
        <div className="mx-auto max-w-[1240px]">
          <p className="text-center text-[18px] font-bold tracking-[0.18em] text-primary-dark md:text-[22px]">
            FITUR
          </p>
          <h2 className="mt-4 text-[32px] font-extrabold md:text-[46px]">
            Solusi Cerdas untuk Bisnis
          </h2>
          <p className="mt-3 max-w-[1050px] text-[15px] leading-relaxed md:text-[19px]">
            Dari prediksi banjir hingga rute alternatif, ARUNA membantu bisnis menghadapi gangguan dengan lebih siap.
          </p>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
            {features.map(([title, description], index) => (
              <article
                key={title}
                className="flex min-h-[320px] flex-col rounded-[22px] bg-white/80 px-5 py-7 text-center text-black shadow-sm backdrop-blur-sm transition hover:-translate-y-1 hover:shadow-lg"
              >
                <span className="mx-auto grid size-[56px] place-items-center rounded-full bg-accent text-[24px] font-bold text-white shadow-md">
                  {index + 1}
                </span>
                <h3 className="mt-5 text-[17px] font-bold leading-tight">{title}</h3>
                <p className="mt-4 text-[13px] font-medium leading-relaxed text-[#5a5a5a]">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[linear-gradient(180deg,#eba92d,#a16d12)] px-8 py-24 text-center md:px-14 lg:px-16">
        <div className="mx-auto max-w-[1240px]">
          <h2 className="text-[32px] font-extrabold md:text-[44px]">
            Bangun Ketahanan Bisnis Anda
          </h2>
          <p className="mx-auto mt-4 max-w-[760px] text-[15px] leading-relaxed md:text-[18px]">
            Uji skenario banjir, pahami dampaknya, dan siapkan keputusan pemulihan sebelum gangguan terjadi.
          </p>
          <Link
            href="/scenario"
            className="mt-8 inline-flex min-h-[64px] min-w-[min(100%,460px)] items-center justify-center rounded-full bg-primary-dark px-9 text-[15px] font-bold text-white shadow-xl transition hover:bg-primary active:scale-95"
          >
            CREATE YOUR SCENARIO HERE
          </Link>
        </div>
      </section>

      <footer className="flex min-h-[120px] items-center bg-primary-dark px-8 md:px-14 lg:px-16">
        <div className="mx-auto flex w-full max-w-[1240px] items-center gap-3">
          <Image
            src="/logo-aruna.png"
            alt="ARUNA Logo"
            width={48}
            height={28}
            className="h-8 w-auto object-contain"
          />
          <span className="text-[22px] font-bold tracking-wide">ARUNA</span>
        </div>
      </footer>
    </main>
  );
}
