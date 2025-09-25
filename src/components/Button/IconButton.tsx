import React from 'react';
import styles from './IconButton.module.css';

interface IconButtonProps {
  onClick?: () => void;
  children: React.ReactNode;
}

const IconButton: React.FC<IconButtonProps> = ({ onClick, children }) => {
  return (
    <button onClick={onClick} className={styles.button}>
      <span className={styles.icon}>{children}</span>
    </button>
  );
};

export default IconButton;
