import React from "react";
import {
  LineChart,
  Line,
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
  return (
    <div className={styles.chart}>
      <h3 className="TitleS">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey={dataKey} stroke={color} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricChart;