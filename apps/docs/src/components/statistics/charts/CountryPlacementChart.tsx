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
import type { CountryAggregate } from '../types';

interface Props {
  data: CountryAggregate[];
  topN?: number;
}

export default function CountryPlacementChart({ data, topN = 20 }: Props) {
  const chartData = data
    .sort((a, b) => a.avg_placement - b.avg_placement)
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      placement: parseFloat(c.avg_placement.toFixed(2)),
      vp: Math.round(c.avg_final_vp),
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 26)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 4, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          tickFormatter={(v) => `#${v}`}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          width={95}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, _: string, props) => [
            `#${value} avg rank · ${props.payload.vp} avg VP`,
            'Placement',
          ]}
        />
        <Bar dataKey="placement" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.placement <= 3 ? '#50c878' : entry.placement <= 6 ? '#f5a623' : '#e74c3c'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
