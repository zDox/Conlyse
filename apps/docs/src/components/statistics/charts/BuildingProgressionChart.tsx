import React, { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { BuildingAggregate, CountryTimeSeries } from '../types';

interface Props {
  timeseries: CountryTimeSeries[];
  buildings: BuildingAggregate[];
  pct_buckets: number[];
  topNCountries?: number;
}

const COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
  '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
];

interface BuildingTypeOption {
  key: string;
  uid: string;
  tier: number;
  label: string;
}

export default function BuildingProgressionChart({ timeseries, buildings, pct_buckets, topNCountries = 8 }: Props) {
  const topBuildingTypes = useMemo(() => {
    const options: Array<BuildingTypeOption & { score: number }> = [];
    for (const b of buildings) {
      for (const [tierStr, avg] of Object.entries(b.avg_per_tier)) {
        if (!avg) continue;
        const tier = Number(tierStr);
        options.push({
          key: `${b.upgrade_identifier}::${tier}`,
          uid: b.upgrade_identifier,
          tier,
          label: `${b.upgrade_identifier} — Tier ${tier}`,
          score: avg,
        });
      }
    }
    return options.sort((a, b) => b.score - a.score).slice(0, 12);
  }, [buildings]);

  const [selectedKey, setSelectedKey] = useState<string>(topBuildingTypes[0]?.key ?? '');

  const selected = useMemo(
    () => topBuildingTypes.find((o) => o.key === selectedKey),
    [topBuildingTypes, selectedKey],
  );

  const topCountries = useMemo(
    () => [...timeseries]
      .filter((c) => selected && c.building_type_pct_game?.[selected.uid]?.[String(selected.tier)]?.length)
      .sort((a, b) => b.games_played - a.games_played)
      .slice(0, topNCountries),
    [timeseries, selected, topNCountries],
  );

  const chartData = useMemo(() => {
    return pct_buckets.map((b) => {
      const row: Record<string, number | null> = { pct: b };
      for (const c of topCountries) {
        const pts = (selected && c.building_type_pct_game?.[selected.uid]?.[String(selected.tier)]) ?? [];
        const pt = pts.find((p) => p.bucket === b);
        row[c.nation_name] = pt ? pt.avg_count : null;
      }
      return row;
    });
  }, [pct_buckets, topCountries, selected]);

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, color: 'var(--ifm-font-color-base)' }}>Building type:</span>
        <select
          value={selectedKey}
          onChange={(e) => setSelectedKey(e.target.value)}
          style={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            color: 'var(--ifm-font-color-base)',
            borderRadius: 4,
            padding: '3px 8px',
            fontSize: 13,
          }}
        >
          {topBuildingTypes.map((o) => (
            <option key={o.key} value={o.key}>{o.label}</option>
          ))}
        </select>
      </div>
      <ResponsiveContainer width="100%" height={380}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" />
          <XAxis
            dataKey="pct"
            type="number"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: 'var(--ifm-font-color-base)', fontSize: 11 }}
            label={{ value: 'Game progress (%)', position: 'insideBottom', offset: -12, fill: 'var(--ifm-font-color-base)', fontSize: 11 }}
          />
          <YAxis
            tick={{ fill: 'var(--ifm-font-color-base)', fontSize: 11 }}
            label={{ value: 'Avg count', angle: -90, position: 'insideLeft', offset: 10, fill: 'var(--ifm-font-color-base)', fontSize: 11 }}
          />
          <Tooltip
            formatter={(value: number | null, name: string) => [value != null ? value.toFixed(2) : '—', name]}
            labelFormatter={(label) => `${label}% of game`}
            contentStyle={{ background: 'var(--ifm-background-surface-color)', border: '1px solid var(--ifm-color-emphasis-300)', fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          {topCountries.map((c, i) => (
            <Line
              key={c.nation_name}
              type="monotone"
              dataKey={c.nation_name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
