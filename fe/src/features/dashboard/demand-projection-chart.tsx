import type { DashboardSummary } from "@/domain/dashboard";
import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import styles from "./dashboard.module.css";

const WIDTH = 1180;
const HEIGHT = 250;
const LEFT = 94;
const RIGHT = 28;
const TOP = 20;
const BOTTOM = 56;

function pointsFor(series: Array<number | null>, min: number, max: number) {
  const drawableWidth = WIDTH - LEFT - RIGHT;
  const drawableHeight = HEIGHT - TOP - BOTTOM;
  return series
    .map((value, index) => value === null ? null : `${LEFT + (index * drawableWidth) / (series.length - 1)},${TOP + ((max - value) / (max - min || 1)) * drawableHeight}`)
    .filter((point): point is string => point !== null)
    .join(" ");
}

export function DemandProjectionChart({ data, locale }: { data: DashboardSummary["demandProjection"]; locale: InventoryLocale }) {
  const values = data.flatMap((point) => [point.actual, point.predicted]).filter((value): value is number => value !== null);
  const min = Math.floor(Math.min(...values, 0) / 10) * 10;
  const max = Math.max(min + 10, Math.ceil(Math.max(...values, 0) / 10) * 10);
  const gridValues = Array.from({ length: 5 }, (_, index) => max - ((max - min) * index) / 4);

  return (
    <section aria-labelledby="projection-title">
      <h2 id="projection-title" className={styles.sectionTitle}>{locale === "en" ? "Demand Projection" : "Proyeksi Permintaan"}</h2>
      <div className={styles.chartCard}>
        <div className={styles.chartLegend} aria-label="Legenda grafik">
          <span><i className={styles.actualKey} />{locale === "en" ? "History" : "Riwayat"}</span>
          <span><i className={styles.predictedKey} />{locale === "en" ? "Forecast" : "Prediksi"}</span>
        </div>
        <svg className={styles.chart} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby="chart-title chart-description">
          <title id="chart-title">{locale === "en" ? "Historical and forecast demand" : "Grafik riwayat dan prediksi permintaan"}</title>
          <desc id="chart-description">{locale === "en" ? "Dated demand history and a three-day forecast." : "Riwayat permintaan bertanggal dan prediksi tiga hari."}</desc>
          {gridValues.map((value, index) => {
            const y = TOP + (index * (HEIGHT - TOP - BOTTOM)) / 4;
            return <g key={value}><line x1={LEFT} y1={y} x2={WIDTH - RIGHT} y2={y} className={styles.gridLine} /><text x={LEFT - 18} y={y + 6} textAnchor="end" className={styles.axisText}>{Math.round(value)}</text></g>;
          })}
          <line x1={LEFT} y1={TOP} x2={LEFT} y2={HEIGHT - BOTTOM} className={styles.axisLine} />
          <line x1={LEFT} y1={HEIGHT - BOTTOM} x2={WIDTH - RIGHT} y2={HEIGHT - BOTTOM} className={styles.axisLine} />
          <polyline points={pointsFor(data.map((point) => point.actual), min, max)} className={styles.actualLine} />
          <polyline points={pointsFor(data.map((point) => point.predicted), min, max)} className={styles.predictedLine} />
          {data.map((point, index) => {
            const x = LEFT + (index * (WIDTH - LEFT - RIGHT)) / (data.length - 1);
            return <text key={point.label} x={x} y={HEIGHT - 23} textAnchor="middle" className={styles.axisText}>{locale === "en" && point.label === "Hari Ini" ? "Today" : point.label}</text>;
          })}
          <text x={24} y={(TOP + HEIGHT - BOTTOM) / 2} textAnchor="middle" transform={`rotate(-90 24 ${(TOP + HEIGHT - BOTTOM) / 2})`} className={styles.axisLabel}>{locale === "en" ? "PRODUCTS SOLD" : "PRODUK TERJUAL"}</text>
          <text x={(LEFT + WIDTH - RIGHT) / 2} y={HEIGHT - 2} textAnchor="middle" className={styles.axisLabel}>{locale === "en" ? "DATE" : "TANGGAL"}</text>
        </svg>
      </div>
    </section>
  );
}
