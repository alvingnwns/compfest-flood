import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import type { DemandForecast } from "@/domain/demand-forecast";
import styles from "./demand-forecast.module.css";

const WIDTH = 1100;
const HEIGHT = 250;
const LEFT = 86;
const RIGHT = 26;
const TOP = 26;
const BOTTOM = 54;

function coordinates(series: Array<number | null>, min: number, max: number) {
  const drawableWidth = WIDTH - LEFT - RIGHT;
  const drawableHeight = HEIGHT - TOP - BOTTOM;
  return series.map((value, index) => value === null ? null : {
    x: LEFT + (index * drawableWidth) / Math.max(1, series.length - 1),
    y: TOP + ((max - value) / (max - min || 1)) * drawableHeight,
  });
}

export function ForecastChart({ points, locale }: { points: DemandForecast["points"]; locale: InventoryLocale }) {
  const todayIndex = points.findIndex((point) => point.label === "Hari Ini" || point.label === "Today");
  const todayX = todayIndex < 0 ? undefined : LEFT + (todayIndex * (WIDTH - LEFT - RIGHT)) / Math.max(1, points.length - 1);
  const sources = [...new Set(points.filter((point) => point.actual !== null).map((point) => point.historySource ?? "UNKNOWN"))];
  const historyLabel = sources.length === 1 && sources[0] === "OBSERVED_SALES" ? (locale === "en" ? "Observed sales" : "Penjualan tercatat") : sources.length === 1 && sources[0] === "SYNTHETIC_DEMAND" ? (locale === "en" ? "Synthetic history" : "Riwayat sintetis") : (locale === "en" ? "History (mixed or unspecified)" : "Riwayat (campuran atau tidak diketahui)");
  const values = points.flatMap((point) => [point.actual, point.predicted]).filter((value): value is number => value !== null);
  const min = Math.floor(Math.min(...values, 0) / 10) * 10;
  const max = Math.max(min + 10, Math.ceil(Math.max(...values, 0) / 10) * 10);
  const actual = coordinates(points.map((point) => point.actual), min, max);
  const predicted = coordinates(points.map((point) => point.predicted), min, max);
  const toSegments = (items: Array<{ x: number; y: number } | null>) => {
    const segments: string[][] = [];
    let current: string[] = [];
    for (const item of items) {
      if (item === null) { if (current.length) segments.push(current); current = []; }
      else current.push(`${item.x},${item.y}`);
    }
    if (current.length) segments.push(current);
    return segments.map((segment) => segment.join(" "));
  };

  return (
    <section aria-labelledby="forecast-chart-title">
      <h2 id="forecast-chart-title" className={styles.sectionTitle}>{locale === "en" ? "Demand Projection" : "Proyeksi Permintaan"}</h2>
      <div className={styles.chartCard}>
        <div className={styles.legend}>{points.some((point) => point.actual !== null) && <span><i className={styles.actualKey} />{historyLabel}</span>}{points.some((point) => point.predicted !== null) && <span><i className={styles.predictedKey} />{locale === "en" ? "Forecast" : "Prediksi"}</span>}</div>
        <svg className={styles.chart} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby="forecast-svg-title forecast-svg-description">
          <title id="forecast-svg-title">{locale === "en" ? "Product demand projection" : "Proyeksi permintaan produk"}</title>
          <desc id="forecast-svg-description">{locale === "en" ? "Demand for the selected date range. Missing values are left blank." : "Permintaan pada rentang tanggal yang dipilih. Nilai yang belum tersedia dibiarkan kosong."}</desc>
          {[0, 1, 2].map((index) => { const y = TOP + (index * (HEIGHT - TOP - BOTTOM)) / 2; const value = max - ((max - min) * index) / 2; return <g key={value}><line x1={LEFT} y1={y} x2={WIDTH - RIGHT} y2={y} className={styles.gridLine} /><text x={LEFT - 16} y={y + 5} textAnchor="end" className={styles.axisText}>{Math.round(value)}</text></g>; })}
          <line x1={LEFT} y1={TOP} x2={LEFT} y2={HEIGHT - BOTTOM} className={styles.axisLine} />
          <line x1={LEFT} y1={HEIGHT - BOTTOM} x2={WIDTH - RIGHT} y2={HEIGHT - BOTTOM} className={styles.axisLine} />
          {todayX !== undefined && <line x1={todayX} y1={TOP} x2={todayX} y2={HEIGHT - BOTTOM} className={styles.todayLine} />}
          {toSegments(actual).map((segment, index) => <polyline key={index} points={segment} className={styles.actualLine} />)}
          {toSegments(predicted).map((segment, index) => <polyline key={index} points={segment} className={styles.predictedLine} />)}
          {actual.filter((item): item is { x: number; y: number } => item !== null).map((item) => <circle key={`a-${item.x}`} cx={item.x} cy={item.y} r="5" className={styles.actualDot} />)}
          {predicted.filter((item): item is { x: number; y: number } => item !== null).map((item) => <circle key={`p-${item.x}`} cx={item.x} cy={item.y} r="5" className={styles.predictedDot} />)}
          {points.map((point, index) => { const x = LEFT + (index * (WIDTH - LEFT - RIGHT)) / Math.max(1, points.length - 1); return <text key={point.label} x={x} y={HEIGHT - 22} textAnchor="middle" className={index === todayIndex ? styles.todayText : styles.axisText}>{locale === "en" && point.label === "Hari Ini" ? "Today" : point.label}</text>; })}
          <text x={20} y={(TOP + HEIGHT - BOTTOM) / 2} textAnchor="middle" transform={`rotate(-90 20 ${(TOP + HEIGHT - BOTTOM) / 2})`} className={styles.axisLabel}>{locale === "en" ? "PRODUCTS SOLD" : "PRODUK TERJUAL"}</text>
          <text x={(LEFT + WIDTH - RIGHT) / 2} y={HEIGHT - 2} textAnchor="middle" className={styles.axisLabel}>{locale === "en" ? "DATE" : "TANGGAL"}</text>
        </svg>
      </div>
    </section>
  );
}
