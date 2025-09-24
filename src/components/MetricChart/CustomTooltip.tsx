import type {
  NameType,
  Payload,
  ValueType,
} from 'recharts/types/component/DefaultTooltipContent';
import styles from './MetricChart.module.css';

interface CustomTooltipProps {
  active?: boolean;
  payload?: Payload<ValueType, NameType>[];
  label?: string | number;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const timeLabel = label ? String(label) : '';

    return (
      <div className={styles.customTooltip}>
        <p className={styles.tooltipLabel}>{timeLabel}</p>
        <ul className={styles.tooltipList}>
          {payload.map((p, index) => {
            const seriesName = p.name as string;
            const seriesValue = p.value as number;
            const seriesColor = p.color;

            const formattedValue =
              typeof seriesValue === 'number'
                ? seriesValue.toLocaleString()
                : seriesValue;

            // unit은 payload에서 직접 가져올 수 없으므로 빈 문자열로 처리
            const unit = '';

            return (
              <li key={`item-${index}`} className={styles.tooltipItem}>
                <div className={styles.itemLeft}>
                  <div
                    className={styles.itemColorIndicator}
                    style={{ backgroundColor: seriesColor }}
                  ></div>
                  <span className={styles.itemName}>{seriesName}</span>
                </div>
                <span className={styles.itemValue}>
                  {`${formattedValue}${unit}`}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  return null;
};

export default CustomTooltip;
