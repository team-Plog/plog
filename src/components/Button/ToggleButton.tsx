import React from 'react';
import styles from './ToggleButton.module.css';

interface ToggleOption {
  value: string;
  label: string;
  icon: React.ReactNode;
}

interface ToggleButtonProps {
  options: ToggleOption[];
  selectedValue: string;
  onChange: (value: string) => void;
}

const ToggleButton: React.FC<ToggleButtonProps> = ({
  options,
  selectedValue,
  onChange,
}) => {
  return (
    <div className={styles.container}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`${styles.option} ${
            selectedValue === option.value ? styles.selected : ''
          }`}
          onClick={() => onChange(option.value)}
        >
          <span className={styles.icon}>{option.icon}</span>
          <span className={`${styles.label} Body`}>{option.label}</span>
        </button>
      ))}
    </div>
  );
};

export default ToggleButton;
