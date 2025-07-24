// src/components/Button/Button.tsx
import React from 'react';
import styles from './Button.module.css';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primaryGradient' | 'secondary';
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  useInlineStyle?: boolean; // CSS 클래스 vs 인라인 스타일 선택
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primaryGradient',
  onClick,
  disabled = false,
  type = 'button',
  className = '',
  useInlineStyle = false,
}) => {
  if (!useInlineStyle) {
    const buttonClass = variant === 'primaryGradient' 
      ? styles.buttonPrimaryGradient 
      : styles.buttonSecondary;

    return (
      <button
        type={type}
        className={`${buttonClass} ${className}`}
        onClick={onClick}
        disabled={disabled}
      >
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