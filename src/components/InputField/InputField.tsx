import React from "react";
import styles from "./InputField.module.css";

interface InputFieldProps {
  title?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
}

const InputField: React.FC<InputFieldProps> = ({ title, placeholder, value, onChange }) => {
  return (
    <div className={styles.container}>
      {title && <label className={styles.title}>{title}</label>}
      <input
        type="text"
        className={styles.input}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && (
        <button
          onClick={() => onChange("")}
          className={styles.clearButton}
        >
          ×
        </button>
      )}
    </div>
  );
};

export default InputField;
