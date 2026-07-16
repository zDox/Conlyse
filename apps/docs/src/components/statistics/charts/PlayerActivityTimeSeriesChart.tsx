import React, { useState } from 'react';
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
import type { TimeSeriesOutput } from '../types';

interface Props {
  data: TimeSeriesOutput;
}

type Mode = 'pct' | 'days';

const LINES = [
  { key: 'alive',         label: 'Total Alive',    color: '#4a90e2' },
  { key: 'active_human',  label: 'Active Humans',  color: '#50c878' },
  { key: 'passive_human', label: 'Passive Humans', color: '#f5a623' },
  { key: 'ai',            label: 'Native AI',      color: '#e74c3c' },
] as const;

export default function PlayerActivityTimeSeriesChart({ data }: Props) {
  const [mode, setMode] = useState<Mode>('pct');

  const series = mode === 'pct' ? data.player_activity_pct : data.player_activity_days;

  const chartData = series.map((p) => ({
    bucket: p.bucket,
    alive: p.avg_alive,
    active_human: p.avg_active_human,
    passive_human: p.avg_passive_human,
    ai: p.avg_ai,
  }));

  const xInterval = mode === 'pct' ? 3 : Math.max(1, Math.floor(data.max_game_days / 10));

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
        <button
          onClick={() => setMode('pct')}
          style={{
            padding: '4px 14px',
            borderRadius: 4,
            border: '1px solid var(--ifm-color-emphasis-300)',
            background: mode === 'pct' ? 'var(--ifm-color-primary)' : 'transparent',
            color: mode === 'pct' ? '#fff' : 'var(--ifm-font-color-base)',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          % of Game
        </button>
        <button
          onClick={() => setMode('days')}
          style={{
            padding: '4px 14px',
            borderRadius: 4,
            border: '1px solid var(--ifm-color-emphasis-300)',
            background: mode === 'days' ? 'var(--ifm-color-primary)' : 'transparent',
            color: mode === 'days' ? '#fff' : 'var(--ifm-font-color-base)',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          Game Days
        </button>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" />
          <XAxis
            dataKey="bucket"
            tickFormatter={(v) => mode === 'pct' ? `${v}%` : `Day ${v}`}
            tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
            interval={xInterval}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
            allowDecimals={true}
            label={{
              value: 'Players',
              angle: -90,
              position: 'insideLeft',
              offset: 12,
              style: { fontSize: 11, fill: 'var(--ifm-font-color-base)' },
            }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--ifm-background-surface-color)',
              border: '1px solid var(--ifm-color-emphasis-300)',
              borderRadius: 6,
              color: 'var(--ifm-font-color-base)',
            }}
            formatter={(value: number, name: string) => {
              const line = LINES.find((l) => l.key === name);
              return [value.toFixed(1), line?.label ?? name];
            }}
            labelFormatter={(label) => (mode === 'pct' ? `${label}% of game` : `Day ${label}`)}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value) => LINES.find((l) => l.key === value)?.label ?? value}
          />
          {LINES.map(({ key, color }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={color}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
