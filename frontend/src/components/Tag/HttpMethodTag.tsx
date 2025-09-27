import React from 'react';
import styles from './Tag.module.css';
import type { HttpMethodTagProps } from './types';
import { HTTP_METHOD_STYLES } from './constants';

const HttpMethodTag: React.FC<HttpMethodTagProps> = ({ 
  method, 
  className = '' 
}) => {
  const styleConfig = HTTP_METHOD_STYLES[method];

  return (
    <span 
      className={`${styles.httpMethod} ${className} CaptionBold`}
      style={{
        color: styleConfig.color,
        backgroundColor: styleConfig.background,
      }}
    >
      {method}
    </span>
  );
};

export default HttpMethodTag;