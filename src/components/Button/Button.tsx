import React, { useState, useRef, useEffect } from 'react';
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
  responsive?: boolean; // 반응형 모드 활성화
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primaryGradient',
  onClick,
  disabled = false,
  type = 'button',
  className = '',
  useInlineStyle = false,
  icon,
  responsive = false
}) => {
  const [isTextHidden, setIsTextHidden] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!responsive || !buttonRef.current || !textRef.current) return;

    const checkTextOverflow = () => {
      const button = buttonRef.current;
      const text = textRef.current;
      
      if (!button || !text) return;

      // CSS 변수 값들 (실제 디자인 시스템 값)
      const iconSize = icon ? 16 : 0; // --icon-size-md
      const spacingSm = 8; // --spacing-sm
      const spacingLg = 16; // --spacing-lg
      
      const buttonWidth = button.offsetWidth;
      const padding = spacingSm * 2 + spacingLg * 2; // 좌우 패딩
      const minWidthForText = iconSize + padding + 80; // 텍스트 표시를 위한 최소 너비
      
      setIsTextHidden(buttonWidth < minWidthForText);
    };

    // ResizeObserver로 버튼 크기 변화 감지
    const resizeObserver = new ResizeObserver(checkTextOverflow);
    resizeObserver.observe(buttonRef.current);

    // 초기 체크
    checkTextOverflow();

    return () => resizeObserver.disconnect();
  }, [responsive, icon]);

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

    const finalClassName = `${buttonClass} ${responsive ? styles.responsive : ''} ${isTextHidden ? styles.textHidden : ''} ${className}`.trim();

    return (
      <button
        ref={buttonRef}
        type={type}
        className={finalClassName}
        onClick={onClick}
        disabled={disabled}
        title={responsive && isTextHidden ? children?.toString() : undefined} // 툴팁 제공
      >
        {icon && <span className={styles.iconWrapper}>{icon}</span>}
        {responsive ? (
          <span 
            ref={textRef}
            className={styles.textContent}
            style={{ 
              display: isTextHidden ? 'none' : 'inline',
            }}
          >
            {children}
          </span>
        ) : (
          children
        )}
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