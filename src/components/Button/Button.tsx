import React from 'react';
import styles from './Button.module.css';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primaryGradient' | 'secondary' | 'warning';
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  useInlineStyle?: boolean; // CSS 클래스 vs 인라인 스타일 선택
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primaryGradient',
  onClick,
  disabled = false,
  type = 'button',
  className = '',
  useInlineStyle = false,
  icon
}) => {
  if (!useInlineStyle) {
    let buttonClass = styles.buttonSecondary; // 기본값
    
    switch (variant) {
      case 'primaryGradient':
        buttonClass = styles.buttonPrimaryGradient;
        break;
      case 'secondary':
        buttonClass = styles.buttonSecondary;
        break;
      case 'warning':
        buttonClass = styles.buttonWarning;
        break;
    }

    return (
      <button
        type={type}
        className={`${buttonClass} ${className}`}
        onClick={onClick}
        disabled={disabled}
      >
        {icon && <span className={styles.iconWrapper}>{icon}</span>}
        {children}
      </button>
    );
  }

  return (
    <button
      type={type}
      className={className}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};