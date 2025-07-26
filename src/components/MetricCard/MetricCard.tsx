import React from 'react';
import styles from './MetricCard.module.css';
import type { MetricCardProps } from '../ProjectCard/types';

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, className = "" }) => {
  return (
    <div className={`${styles.card} ${className}`}>
      <div className={styles.iconLabelGroup}>
        <div className={styles.iconWrapper}>{icon}</div>
        <div className="Body">{label}</div>
      </div>
      <div className="HeadingL">{value}</div>
    </div>
  );
};

export default MetricCard;
