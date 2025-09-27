import React from "react";
import styles from "./MetricCard.module.css";
import type {MetricCardProps} from "../ProjectCard/types";

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  color,
  className = "",
}) => {
  const getIconClass = () => {
    if (label.includes("TPS")) return styles.tps;
    if (label.includes("응답")) return styles.response;
    if (label.includes("에러")) return styles.error;
    if (label.includes("사용자")) return styles.user;
    return "";
  };

  return (
    <div className={`${styles.card} ${className}`}>
      <div className={styles.iconLabelGroup}>
        <div className={`${styles.iconWrapper} ${getIconClass()}`}>{icon}</div>
        <div className="Body">{label}</div>
      </div>
      <div className={`HeadingL ${styles.value}`}>{value}</div>
    </div>
  );
};

export default MetricCard;
