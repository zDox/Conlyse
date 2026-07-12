import React, { useMemo } from 'react';
import {
  CartesianGrid,
  Label,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ProvinceAggregate } from '../types';

interface Props {
  data: ProvinceAggregate[];
}

const REGION_COLOURS: Record<string, string> = {
  EUROPA:        '#2a78d6',
  ASIA:          '#1baf7a',
  AFRICA:        '#eda100',
  NORTH_AMERICA: '#008300',
  SOUTH_AMERICA: '#4a3aa7',
  OCEANIA:       '#e34948',
  NONE:          '#9a9a9a',
};

const REGION_LABELS: Record<string, string> = {
  EUROPA:        'Europe',
  ASIA:          'Asia',
  AFRICA:        'Africa',
  NORTH_AMERICA: 'North America',
  SOUTH_AMERICA: 'South America',
  OCEANIA:       'Oceania',
  NONE:          'Unknown',
};

function formatRegion(region: string): string {
  return REGION_LABELS[region] ?? region;
}

const QUADRANT_STYLE = {
  fontSize: 10,
  fill: 'var(--ifm-color-emphasis-500)',
  fontStyle: 'italic' as const,
};

interface ScatterPoint {
  name: string;
  region: string;
  changes: number;
  winCorr: number;
  fill: string;
}

const OUTLIER_N = 10;

function median(sorted: number[]): number {
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function buildOutlierSet(points: ScatterPoint[]): Set<string> {
  const top = (sorted: ScatterPoint[]) => sorted.slice(0, OUTLIER_N).map((p) => p.name);
  return new Set([
    ...top([...points].sort((a, b) => b.winCorr - a.winCorr)),
    ...top([...points].sort((a, b) => b.changes - a.changes)),
    ...top([...points].sort((a, b) => (b.changes * b.winCorr) - (a.changes * a.winCorr))),
  ]);
}

function makeDotRenderer(outliers: Set<string>, medChanges: number, medWinCorr: number) {
  return function CustomDot(props: { cx?: number; cy?: number; payload?: ScatterPoint }) {
    const { cx = 0, cy = 0, payload } = props;
    if (!payload) return null;
    const isOutlier = outliers.has(payload.name);

    const labelRight = payload.changes > medChanges;
    const labelAbove = payload.winCorr < medWinCorr;
    const lx = labelRight ? cx - 6 : cx + 6;
    const ly = labelAbove ? cy + 11 : cy - 5;

    return (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={isOutlier ? 5 : 3}
          fill={payload.fill}
          fillOpacity={isOutlier ? 0.9 : 0.35}
        />
        {isOutlier && (
          <text
            x={lx}
            y={ly}
            fontSize={9}
            fill="var(--ifm-font-color-base)"
            textAnchor={labelRight ? 'end' : 'start'}
          >
            {payload.name}
          </text>
        )}
      </g>
    );
  };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ScatterPoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div style={{
      background: 'var(--ifm-background-surface-color)',
      border: '1px solid var(--ifm-color-emphasis-300)',
      borderRadius: 6,
      padding: '6px 10px',
      fontSize: 12,
      color: 'var(--ifm-font-color-base)',
      lineHeight: 1.6,
    }}>
      <div style={{ fontWeight: 600 }}>{p.name}</div>
      <div>{formatRegion(p.region)}</div>
      <div>Avg ownership changes: {p.changes.toFixed(2)}</div>
      <div>Winner held in {p.winCorr.toFixed(1)}% of games</div>
    </div>
  );
}

function RegionLegend({ regions }: { regions: string[] }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', marginTop: 10, fontSize: 11, color: 'var(--ifm-font-color-base)' }}>
      {regions.map((r) => (
        <span key={r} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: REGION_COLOURS[r] ?? '#aaa', display: 'inline-block' }} />
          {formatRegion(r)}
        </span>
      ))}
    </div>
  );
}

export default function ProvinceStrategicScatterChart({ data }: Props) {
  const points = useMemo<ScatterPoint[]>(
    () => data.map((p) => ({
      name: p.province_name,
      region: p.region,
      changes: parseFloat(p.avg_ownership_changes.toFixed(2)),
      winCorr: parseFloat((p.win_correlation * 100).toFixed(2)),
      fill: REGION_COLOURS[p.region] ?? '#aaaaaa',
    })),
    [data],
  );

  const { medChanges, medWinCorr, xMin, xMax, yMin, yMax } = useMemo(() => {
    const changes = [...points].map((p) => p.changes).sort((a, b) => a - b);
    const winCorrs = [...points].map((p) => p.winCorr).sort((a, b) => a - b);
    return {
      medChanges: parseFloat(median(changes).toFixed(2)),
      medWinCorr: parseFloat(median(winCorrs).toFixed(1)),
      xMin: Math.floor(changes[0] * 2) / 2,
      xMax: parseFloat((Math.ceil(changes[changes.length - 1] * 2) / 2 + 0.25).toFixed(2)),
      yMin: Math.floor(winCorrs[0] / 5) * 5,
      yMax: Math.ceil(winCorrs[winCorrs.length - 1] / 5) * 5 + 2,
    };
  }, [points]);

  const outlierSet = useMemo(() => buildOutlierSet(points), [points]);
  const regions = useMemo(() => [...new Set(points.map((p) => p.region))].sort(), [points]);
  const CustomDot = useMemo(() => makeDotRenderer(outlierSet, medChanges, medWinCorr), [outlierSet, medChanges, medWinCorr]);

  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--ifm-color-emphasis-500)', marginBottom: 4 }}>
        Reference lines at medians — ownership changes {medChanges} · winner control {medWinCorr}%
      </div>
      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 24, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-200)" />
          <XAxis
            type="number"
            dataKey="changes"
            domain={[xMin, xMax]}
            tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
            label={{ value: 'Avg ownership changes →', position: 'insideBottom', offset: -14, fontSize: 11, fill: 'var(--ifm-color-emphasis-500)' }}
          />
          <YAxis
            type="number"
            dataKey="winCorr"
            domain={[yMin, yMax]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
            label={{ value: '← Winner control', angle: -90, position: 'insideLeft', offset: 14, fontSize: 11, fill: 'var(--ifm-color-emphasis-500)' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={medChanges} stroke="var(--ifm-color-emphasis-400)" strokeDasharray="4 4">
            <Label value="High turnover →" position="insideTopRight" style={QUADRANT_STYLE} />
            <Label value="← Stable" position="insideTopLeft" style={QUADRANT_STYLE} />
          </ReferenceLine>
          <ReferenceLine y={medWinCorr} stroke="var(--ifm-color-emphasis-400)" strokeDasharray="4 4">
            <Label value="Core strategic" position="insideTopRight" style={QUADRANT_STYLE} />
            <Label value="Battlegrounds" position="insideBottomRight" style={QUADRANT_STYLE} />
            <Label value="Key objectives" position="insideTopLeft" style={QUADRANT_STYLE} />
            <Label value="Peripheral" position="insideBottomLeft" style={QUADRANT_STYLE} />
          </ReferenceLine>
          <Scatter data={points} shape={CustomDot} />
        </ScatterChart>
      </ResponsiveContainer>
      <RegionLegend regions={regions} />
    </div>
  );
}
