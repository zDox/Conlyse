import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ProvinceAggregate } from '../types';

interface Props {
  data: ProvinceAggregate[];
  topN?: number;
}

const TERRAIN_COLOURS: Record<string, string> = {
  PLAINS:   '#7bc67a',
  HILLS:    '#b8a05a',
  MOUNTAIN: '#8c9db5',
  FOREST:   '#3a8a4a',
  URBAN:    '#5b7ec9',
  JUNGLE:   '#2e7d52',
  TUNDRA:   '#8ecae6',
  DESERT:   '#e9c46a',
  SUBURBAN: '#9b72cf',
};

function terrainColour(terrain: string): string {
  return TERRAIN_COLOURS[terrain] ?? '#aaaaaa';
}

export default function ProvinceMoraleChart({ data, topN = 20 }: Props) {
  const chartData = [...data]
    .sort((a, b) => b.avg_morale - a.avg_morale)
    .slice(0, topN)
    .map((p) => ({
      name: p.province_name,
      morale: parseFloat(p.avg_morale.toFixed(1)),
      terrain: p.terrain_type,
      coastal: p.is_coastal,
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 24)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 110, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 10, fill: 'var(--ifm-font-color-base)' }}
          width={105}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, _: string, props) => {
            const { terrain, coastal } = props.payload;
            const coastalLabel = coastal ? ' · coastal' : '';
            return [
              `${value}% avg morale · ${terrain}${coastalLabel}`,
              'Avg morale',
            ];
          }}
        />
        <Bar dataKey="morale" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={terrainColour(entry.terrain)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
