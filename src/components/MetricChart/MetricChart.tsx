import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import styles from "./MetricChart.module.css";
import "../../assets/styles/typography.css";

interface MetricChartProps {
  title: string;
  data: any[];
  dataKey: string;
  color: string;
}

const MetricChart: React.FC<MetricChartProps> = ({
  title,
  data,
  dataKey,
  color,
}) => {
  // 그라데이션 ID 생성 (고유성을 위해 dataKey 사용)
  const gradientId = `gradient-${dataKey}`;

  return (
    <div className={styles.chart}>
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.8} />
              <stop offset="100%" stopColor={color} stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="time"
          />
          <YAxis />
          <Tooltip />
          <Area 
            type="monotone" 
            dataKey={dataKey} 
            stroke={color} 
            fill={`url(#${gradientId})`}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricChart;