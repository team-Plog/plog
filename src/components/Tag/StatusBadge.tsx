import React from 'react';
import styles from './Tag.module.css';
import type { StatusBadgeProps } from './types';
import { STATUS_CONFIG } from './constants';

const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  className = '' 
}) => {
  const config = STATUS_CONFIG[status];
  const IconComponent = config.icon;

  return (
    <span 
      className={`${styles.statusBadge} ${className} CaptionBold`}
      style={{
        color: config.color,
        backgroundColor: config.background,
      }}
    >
      <IconComponent className={styles.icon} />
      {config.text}
    </span>
  );
};

export default StatusBadge;