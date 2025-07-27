import React from "react";
import styles from './BaseInput.module.css';

interface BaseInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  title?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRightIconClick?: () => void;
  className?: string;
  variant?: 'gray' | 'white';
  showBoxShadow?: boolean;
  multiline?: boolean;
  leftIconSize?: 'normal' | 'small';
  rightIconSize?: 'normal' | 'small'; // 오른쪽 아이콘도 지원
}

const BaseInput: React.FC<BaseInputProps> = ({
  value,
  onChange,
  placeholder,
  title,
  leftIcon,
  rightIcon,
  onRightIconClick,
  className,
  variant = 'gray',
  showBoxShadow,
  multiline = false,
  leftIconSize = 'normal',
  rightIconSize = 'normal',
}) => {
  const shouldShowBoxShadow = showBoxShadow !== undefined ? showBoxShadow : variant === 'white';
  const inputStyle = `
    ${styles.input} 
    ${variant === 'white' ? styles.inputWhite : styles.inputGray}
    ${shouldShowBoxShadow ? styles.withBoxShadow : ''} 
    ${leftIcon ? styles.withLeftIcon : ''} 
    ${rightIcon ? styles.withRightIcon : ''} 
    ${className || ''}
    ${multiline ? styles.textareaFixed : ''}
  `;

  // 아이콘 클래스 선택
  const leftIconClass = leftIconSize === 'small' ? styles.leftIconSmall : styles.leftIcon;
  const rightIconClass = rightIconSize === 'small' ? styles.rightIconSmall : styles.rightIcon;

  return (
    <div className={styles.inputContainer}>
      {title && <label className={styles.title}>{title}</label>}

      <div className={styles.inputWrapper}>
        {leftIcon && <div className={leftIconClass}>{leftIcon}</div>}

        {multiline ? (
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={inputStyle}
          />
        ) : (
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={inputStyle}
          />
        )}

        {rightIcon && (
          <div className={rightIconClass} onClick={onRightIconClick}>
            {rightIcon}
          </div>
        )}
      </div>
    </div>
  );
};

export default BaseInput;