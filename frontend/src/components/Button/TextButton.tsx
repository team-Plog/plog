import React from 'react';
import styles from './TextButton.module.css';
import '../../assets/styles/typography.css';

interface TextButtonProps {
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  children: React.ReactNode;
  className?: string;
}

const TextButton: React.FC<TextButtonProps> = ({
  onClick,
  children,
  className,
}) => {
  return (
    <button onClick={onClick} className={`${styles.textButton} ${className}`}>
      {children}
    </button>
  );
};

export default TextButton;
