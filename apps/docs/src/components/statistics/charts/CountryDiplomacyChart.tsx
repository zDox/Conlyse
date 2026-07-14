import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { CountryAggregate } from '../types';

interface Props {
  data: CountryAggregate[];
  topN?: number;
  minGames?: number;
}

export default function CountryDiplomacyChart({ data, topN = 20, minGames = 3 }: Props) {
  const chartData = [...data]
    .filter((c) => c.games_played >= minGames)
    .map((c) => ({
      name: c.nation_name,
      wars: parseFloat(c.avg_wars_declared.toFixed(1)),
      rows: parseFloat(c.avg_right_of_ways_signed.toFixed(1)),
      peace: parseFloat(c.avg_peace_treaties_signed.toFixed(1)),
    }))
    .sort((a, b) => (b.wars + b.rows + b.peace) - (a.wars + a.rows + a.peace))
    .slice(0, topN);

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
          allowDecimals={false}
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
          formatter={(value: number, name: string, props) => {
            const { wars, rows, peace } = props.payload;
            return [
              `${value} avg · total ${(wars + rows + peace).toFixed(1)} diplomatic acts`,
              name,
            ];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="wars" name="Wars Declared" stackId="a" fill="#e74c3c" />
        <Bar dataKey="rows" name="Right of Ways" stackId="a" fill="#4a90e2" />
        <Bar dataKey="peace" name="Peace Treaties" stackId="a" fill="#50c878" radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
