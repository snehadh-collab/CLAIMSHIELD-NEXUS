import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";
import "./FinancialForecastView.css";

/* ---------- Simulator constants ---------- */
const HORIZON_DAYS = 90;
const MIN_THRESHOLD = 30;
const MAX_THRESHOLD = 90;
const DEFAULT_THRESHOLD = 70;
const FALLBACK_DAILY_LOSS = 7200; // used only when the forecast endpoint is unreachable / empty
const X_TICKS = [0, 15, 30, 45, 60, 75, 90];

/*
 * Mitigation model (calibrated to the reference design at the 70% reference threshold):
 *   mitigated(day) = baseline(day) * (1 - E(threshold) * ramp(day))
 *   ramp(day)      = 1 - exp(-day / TAU)            -> enforcement takes effect gradually (concave green curve)
 *   E(threshold)   = MAX_INTERCEPT * (1 - u^P)      -> lower cutoff holds more claims => more leakage intercepted
 *                    u = (threshold - 30) / 70
 * At 70%: 42.0% of loss is saved by Day 30 and 66.5% by Day 90 (Day 30 -> Red $216,000 / Green $125,280).
 */
const REF_THRESHOLD = 70;
const REF_SAVED_BY_DAY_30 = 0.42;
const REF_SAVED_BY_DAY_90 = 0.665;
const MAX_INTERCEPT = 0.95;

const RAMP_BASE = (-1 + Math.sqrt(1 + 4 * (REF_SAVED_BY_DAY_90 / REF_SAVED_BY_DAY_30 - 1))) / 2; // e^(-30/TAU)
const TAU = -30 / Math.log(RAMP_BASE);
const REF_INTERCEPT = REF_SAVED_BY_DAY_30 / (1 - RAMP_BASE);
const U_REF = (REF_THRESHOLD - MIN_THRESHOLD) / (MAX_THRESHOLD - MIN_THRESHOLD + 10);
const SHAPE = Math.log(1 - REF_INTERCEPT / MAX_INTERCEPT) / Math.log(U_REF);

function interceptRate(threshold) {
  const u = Math.min(Math.max((threshold - MIN_THRESHOLD) / (MAX_THRESHOLD - MIN_THRESHOLD + 10), 0), 1);
  return MAX_INTERCEPT * (1 - Math.pow(u, SHAPE));
}

function buildSeries(dailyLoss, threshold) {
  const rate = interceptRate(threshold);
  const series = [];
  for (let day = 0; day <= HORIZON_DAYS; day += 1) {
    const baseline = dailyLoss * day;
    const mitigated = baseline * (1 - rate * (1 - Math.exp(-day / TAU)));
    series.push({ day, baseline: Math.round(baseline), mitigated: Math.round(mitigated) });
  }
  return series;
}

/* Pulls the provider's daily loss run-rate out of GET /api/v1/cases/{provider_npi}/forecast */
function dailyLossFrom(payload) {
  const day90 = Number(payload?.day_90_exposure);
  if (Number.isFinite(day90) && day90 > 0) return day90 / HORIZON_DAYS;
  const velocity = Number(payload?.historical_daily_avg_claim);
  if (Number.isFinite(velocity) && velocity > 0) return velocity;
  return null;
}

const usd = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

function SlidersIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  );
}

function SimulatorTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="whatif-tooltip">
      <strong>Day {point.day}</strong>
      <span className="sep">|</span>
      <span className="red">Red: {usd(point.baseline)}</span>
      <span className="sep">|</span>
      <span className="green">Green: {usd(point.mitigated)}</span>
    </div>
  );
}

export default function FinancialForecastView({ providerNpi }) {
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [dailyLoss, setDailyLoss] = useState(FALLBACK_DAILY_LOSS);
  const [source, setSource] = useState("loading"); // "loading" | "live" | "fallback"

  useEffect(() => {
    let cancelled = false;
    setSource("loading");
    api
      .forecast(providerNpi)
      .then((payload) => {
        if (cancelled) return;
        const rate = dailyLossFrom(payload);
        if (rate === null) {
          setDailyLoss(FALLBACK_DAILY_LOSS);
          setSource("fallback");
        } else {
          setDailyLoss(rate);
          setSource("live");
        }
      })
      .catch(() => {
        if (cancelled) return;
        setDailyLoss(FALLBACK_DAILY_LOSS);
        setSource("fallback");
      });
    return () => {
      cancelled = true;
    };
  }, [providerNpi]);

  const data = useMemo(() => buildSeries(dailyLoss, threshold), [dailyLoss, threshold]);
  const last = data[data.length - 1];
  const saved = last.baseline - last.mitigated;
  const yMax = Math.max(800000, Math.ceil(last.baseline / 200000) * 200000);
  const yTicks = useMemo(() => Array.from({ length: yMax / 200000 + 1 }, (_, i) => i * 200000), [yMax]);
  const fillPct = ((threshold - MIN_THRESHOLD) / (MAX_THRESHOLD - MIN_THRESHOLD)) * 100;

  return (
    <section className="whatif-panel" aria-label="What-If Mitigation Simulator">
      <header className="whatif-header">
        <div className="whatif-title-block">
          <h3>
            <SlidersIcon />
            Interactive "What-If" Mitigation Simulator
          </h3>
          <p>Adjust the automated payment hold cutoff threshold to model real-time dollar savings.</p>
        </div>
        <div className="whatif-badge" aria-live="polite">
          <span>PROJECTED SIU SAVINGS</span>
          <strong>{usd(saved)}</strong>
        </div>
      </header>

      <div className="whatif-control">
        <div className="whatif-control-row">
          <label htmlFor="whatif-threshold">Automated Audit Cutoff Threshold:</label>
          <span className="whatif-value">{threshold}% Composite Score</span>
        </div>
        <input
          id="whatif-threshold"
          className="whatif-slider"
          type="range"
          min={MIN_THRESHOLD}
          max={MAX_THRESHOLD}
          step={1}
          value={threshold}
          style={{ "--fill": `${fillPct}%` }}
          onChange={(event) => setThreshold(Number(event.target.value))}
        />
        <div className="whatif-scale">
          <span>30% (Aggressive Hold)</span>
          <span>60% (Balanced Triaging)</span>
          <span>90% (Strict High-Confidence Only)</span>
        </div>
      </div>

      <div className="whatif-chart">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 12, right: 14, bottom: 4, left: 4 }}>
            <defs>
              <linearGradient id="whatifRed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="whatifGreen" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00A86B" stopOpacity={0.75} />
                <stop offset="100%" stopColor="#00875A" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1c2a38" strokeDasharray="3 4" />
            <XAxis
              dataKey="day"
              type="number"
              domain={[0, HORIZON_DAYS]}
              ticks={X_TICKS}
              tickFormatter={(d) => `Day ${d}`}
              tick={{ fill: "#5f7896", fontSize: 11, fontFamily: "ui-monospace, Menlo, monospace" }}
              stroke="#3b4a5a"
            />
            <YAxis
              domain={[0, yMax]}
              ticks={yTicks}
              tickFormatter={(v) => `$${v / 1000}k`}
              tick={{ fill: "#5f7896", fontSize: 11, fontFamily: "ui-monospace, Menlo, monospace" }}
              stroke="#3b4a5a"
              width={52}
            />
            <Tooltip content={<SimulatorTooltip />} cursor={{ stroke: "#3b4a5a", strokeDasharray: "3 3" }} />
            <Area type="monotone" dataKey="baseline" name="Baseline Cumulative Loss" stroke="#ef4444" strokeWidth={2} fill="url(#whatifRed)" isAnimationActive={false} />
            <Area type="monotone" dataKey="mitigated" name="Mitigated Post-Enforcement" stroke="#00A86B" strokeWidth={2.5} fill="url(#whatifGreen)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <footer className="whatif-legend">
        <span><i className="dot red" />Baseline Cumulative Loss</span>
        <span><i className="dot green" />Mitigated Post-Enforcement (Saved: {usd(saved)})</span>
      </footer>
      {source === "fallback" && (
        <p className="whatif-note">Forecast service unavailable - showing the reference run-rate of {usd(FALLBACK_DAILY_LOSS)}/day.</p>
      )}
    </section>
  );
}
