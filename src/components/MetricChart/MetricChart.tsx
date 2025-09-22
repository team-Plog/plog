import React, { useMemo, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import styles from './MetricChart.module.css';
import '../../assets/styles/typography.css';
import CustomTooltip from './CustomTooltip';

interface CombinedSeries {
  key: string;
  name: string;
  color: string;
  unit?: string;
  yAxis?: 'left' | 'right';
}

interface MetricChartProps {
  title: string;
  data: any[];
  dataKey?: string;
  color?: string;
  combinedSeries?: CombinedSeries[];
  height?: number;
  hideTitle?: boolean; // 제목 숨김 옵션
  hideControls?: boolean; // 토글 컨트롤 숨김 옵션
  showLegend?: boolean; // 범례 표시 옵션
  extraInfo?: React.ReactNode;
}

// Y축 값 포맷팅 함수
const formatYAxisValue = (value: number): string => {
  // 값이 0이면 그대로 반환
  if (value === 0) return '0';

  // 절대값이 1000 이상이면 정수로 표시
  if (Math.abs(value) >= 1000) {
    return Math.round(value).toLocaleString();
  }

  // 절대값이 1 이상이면 소수점 1자리까지
  if (Math.abs(value) >= 1) {
    return Number(value.toFixed(1)).toString();
  }

  // 1 미만이면 소수점 3자리까지
  return Number(value.toFixed(3)).toString();
};

const MetricChart: React.FC<MetricChartProps> = ({
  title,
  data,
  dataKey,
  color,
  combinedSeries,
  height = 200,
  hideTitle = false,
  hideControls = false,
  showLegend = true,
  extraInfo,
}) => {
  const multiMode = !!(combinedSeries && combinedSeries.length > 0);

  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries((combinedSeries ?? []).map((s) => [s.key, true]))
  );

  const hasRightAxis = useMemo(
    () =>
      (combinedSeries ?? []).some(
        (s) => (s.yAxis ?? 'left') === 'right' && visible[s.key]
      ),
    [combinedSeries, visible]
  );

  const toggle = (key: string) =>
    setVisible((prev) => ({ ...prev, [key]: !prev[key] }));

  if (multiMode) {
    const activeSeries = (combinedSeries ?? []).filter((s) => visible[s.key]);

    // Y축 색상을 동적으로 찾기
    const yAxisColors = useMemo(() => {
      const leftActive = activeSeries.find(
        (s) => (s.yAxis ?? 'left') === 'left'
      )?.color;
      const rightActive = activeSeries.find((s) => s.yAxis === 'right')?.color;

      // 활성 시리즈가 없을 때를 위한 폴백(전체 정의 중 첫 번째)
      const leftFallback =
        (combinedSeries ?? []).find((s) => (s.yAxis ?? 'left') === 'left')
          ?.color || '#8884d8';
      const rightFallback =
        (combinedSeries ?? []).find((s) => s.yAxis === 'right')?.color ||
        '#82ca9d';

      return {
        left: leftActive ?? leftFallback,
        right: rightActive ?? rightFallback,
      };
    }, [activeSeries, combinedSeries]);

    return (
      <div className={styles.chart}>
        {!hideTitle && <h3 className="HeadingS">{title}</h3>}

        {!hideControls && (
          <div className={styles.toggleGroup}>
            {(combinedSeries ?? []).map((s) => {
              const isOn = visible[s.key];
              return (
                <label
                  key={s.key}
                  className={`${styles.toggleSwitch} CaptionLight`}
                  title={isOn ? '숨기기' : '보이기'}
                >
                  <input
                    type="checkbox"
                    checked={isOn}
                    onChange={() => toggle(s.key)}
                  />
                  <span
                    className={styles.slider}
                    style={{ backgroundColor: isOn ? s.color : '#ccc' }}
                  />
                  <span className={`${styles.toggleLabel} CaptionLight`}>
                    {s.name}
                  </span>
                </label>
              );
            })}
          </div>
        )}

        <ResponsiveContainer width="100%" height={height}>
          <AreaChart
            data={data}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <defs>
              {activeSeries.map((s) => (
                <linearGradient
                  key={s.key}
                  id={`gradient-${s.key}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={s.color} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0.1} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />

            <YAxis
              yAxisId="left"
              stroke={yAxisColors.left}
              tick={{ fill: yAxisColors.left, fontSize: 12 }}
              domain={[0, (dataMax: number) => dataMax * 1.2]}
              tickFormatter={formatYAxisValue}
            />
            {hasRightAxis && (
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke={yAxisColors.right}
                tick={{ fill: yAxisColors.right, fontSize: 12 }}
                domain={[0, (dataMax: number) => dataMax * 1.2]}
                tickFormatter={formatYAxisValue}
              />
            )}

            <Tooltip
              content={<CustomTooltip />}
              formatter={(value: any, name: any, props: any) => {
                const ser = (combinedSeries ?? []).find(
                  (s) => s.key === props.dataKey
                );
                const unit = ser?.unit ? ` ${ser.unit}` : '';
                const v =
                  typeof value === 'number' ? value.toLocaleString() : value;
                return [`${v}${unit}`, ser?.name ?? name];
              }}
            />

            {showLegend && (
              <Legend
                content={() => (
                  <div className={styles.legend}>
                    {combinedSeries?.map((s) => (
                      <span
                        key={s.key}
                        style={{ color: s.color, fontSize: 12 }}
                      >
                        ■ {s.name}
                      </span>
                    ))}
                  </div>
                )}
              />
            )}

            {activeSeries.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                yAxisId={s.yAxis ?? 'left'}
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
          <div className={`${styles.emptyHint} Body`}>
            표시할 그래프가 없습니다. 위에서 선택하세요.
          </div>
        )}

        {extraInfo && (
          <div className={`${styles.extraInfo} Body`}>{extraInfo}</div>
        )}
      </div>
    );
  }

  // 단일 시리즈 모드
  // const gradientId = `gradient-${dataKey}`;
  // return (
  //   <div className={styles.chart}>
  //     {!hideTitle && <h3 className="HeadingS">{title}</h3>}
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
  //         <YAxis
  //           domain={[0, (dataMax: number) => dataMax * 1.2]}
  //           tickFormatter={formatYAxisValue}
  //         />
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
