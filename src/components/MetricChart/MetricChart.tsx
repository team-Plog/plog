import React, {useMemo, useState} from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import styles from "./MetricChart.module.css";
import "../../assets/styles/typography.css";

interface CombinedSeries {
  key: string; 
  name: string; 
  color: string;
  unit?: string; 
  yAxis?: "left" | "right"; 
}

interface MetricChartProps {
  title: string;
  data: any[];
  // 단일 시리즈 모드
  dataKey?: string;
  color?: string;
  // 합친 그래프 모드
  combinedSeries?: CombinedSeries[];
  height?: number;
}

const MetricChart: React.FC<MetricChartProps> = ({
  title,
  data,
  dataKey,
  color,
  combinedSeries,
  height = 200,
}) => {
  const multiMode = !!(combinedSeries && combinedSeries.length > 0);

  // 시리즈 가시성 토글 상태
  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries((combinedSeries ?? []).map((s) => [s.key, true]))
  );

  const hasRightAxis = useMemo(
    () => (combinedSeries ?? []).some((s) => (s.yAxis ?? "left") === "right"),
    [combinedSeries]
  );

  const toggle = (key: string) =>
    setVisible((prev) => ({...prev, [key]: !prev[key]}));

  if (multiMode) {
    const activeSeries = (combinedSeries ?? []).filter((s) => visible[s.key]);

    return (
      <div className={styles.chart}>
        <h3>{title}</h3>

        {/* ---- 토글 버튼 그룹 ---- */}
        <div className={styles.toggleGroup}>
          {(combinedSeries ?? []).map((s) => {
            const isOn = visible[s.key];
            return (
              <label
                key={s.key}
                className={styles.toggleSwitch}
                title={isOn ? "숨기기" : "보이기"}>
                <input
                  type="checkbox"
                  checked={isOn}
                  onChange={() => toggle(s.key)}
                />
                <span
                  className={styles.slider}
                  style={{backgroundColor: isOn ? s.color : "#ccc"}}
                />
                <span className={styles.toggleLabel}>{s.name}</span>
              </label>
            );
          })}
        </div>

        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data}>
            <defs>
              {activeSeries.map((s) => (
                <linearGradient
                  key={s.key}
                  id={`gradient-${s.key}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0.1} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis yAxisId="left" />
            {hasRightAxis && <YAxis yAxisId="right" orientation="right" />}
            <Tooltip
              formatter={(value: any, name: any, props: any) => {
                const ser = (combinedSeries ?? []).find(
                  (s) => s.key === props.dataKey
                );
                const unit = ser?.unit ? ` ${ser.unit}` : "";
                const v =
                  typeof value === "number" ? value.toLocaleString() : value;
                return [`${v}${unit}`, ser?.name ?? name];
              }}
            />
            <Legend />
            {activeSeries.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                yAxisId={s.yAxis ?? "left"}
                stroke={s.color}
                strokeWidth={2}
                fill={`url(#gradient-${s.key})`}
                isAnimationActive={false}
                dot={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>

        {activeSeries.length === 0 && (
          <div className={styles.emptyHint}>
            표시할 그래프가 없습니다. 위에서 선택하세요.
          </div>
        )}
      </div>
    );
  }

  const gradientId = `gradient-${dataKey}`;

  // return (
  //   <div className={styles.chart}>
  //     <h3>{title}</h3>
  //     <ResponsiveContainer width="100%" height={height}>
  //       <AreaChart data={data}>
  //         <defs>
  //           <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
  //             <stop offset="0%" stopColor={color} stopOpacity={0.8} />
  //             <stop offset="100%" stopColor={color} stopOpacity={0.1} />
  //           </linearGradient>
  //         </defs>
  //         <CartesianGrid strokeDasharray="3 3" />
  //         <XAxis dataKey="time" />
  //         <YAxis />
  //         <Tooltip />
  //         <Area
  //           type="monotone"
  //           dataKey={dataKey!}
  //           stroke={color}
  //           fill={`url(#${gradientId})`}
  //           strokeWidth={2}
  //         />
  //       </AreaChart>
  //     </ResponsiveContainer>
  //   </div>
  // );
};

export default MetricChart;
