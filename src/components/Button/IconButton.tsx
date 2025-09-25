import React from 'react';
import styles from './IconButton.module.css';

interface IconButtonProps {
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  children: React.ReactNode;
  className?: string;
}

const IconButton: React.FC<IconButtonProps> = ({
  onClick,
  children,
  className,
}) => {
  return (
    <button onClick={onClick} className={`${styles.button} ${className}`}>
      <span className={styles.icon}>{children}</span>
    </button>
  );
};

export default IconButton;
