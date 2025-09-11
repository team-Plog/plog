import React, { useState, useRef, useEffect } from "react";
import { InputWithIcon } from "../../components/Input";
import styles from "./SelectDropdown.module.css";

export interface SelectDropdownOption {
  value: string;
  label: string;
}

interface SelectDropdownProps {
  options: SelectDropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: React.ReactNode;
}

const SelectDropdown: React.FC<SelectDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder,
  icon,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filteredOptions, setFilteredOptions] = useState(options);
  const containerRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // 옵션 필터링
  useEffect(() => {
    if (!value) {
      setFilteredOptions(options);
    } else {
      const filtered = options.filter(option =>
        option.label.toLowerCase().includes(value.toLowerCase()) ||
        option.value.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredOptions(filtered);
    }
  }, [value, options]);

  const handleInputChange = (newValue: string) => {
    onChange(newValue);
    if (!isOpen && newValue) {
      setIsOpen(true);
    }
  };

  const handleInputClick = () => {
    setIsOpen(true);
  };

  const handleOptionClick = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  return (
    <div className={styles.container} ref={containerRef}>
      <div onClick={handleInputClick}>
        <InputWithIcon
          icon={icon}
          value={value}
          onChange={handleInputChange}
          placeholder={placeholder}
        />
      </div>
      
      {isOpen && filteredOptions.length > 0 && (
        <div className={styles.dropdown}>
          <div className={styles.optionsList}>
            {filteredOptions.map((option) => (
              <div
                key={option.value}
                className={styles.option}
                onClick={() => handleOptionClick(option.value)}
              >
                <span className={styles.optionLabel}>{option.label}</span>
                {option.value !== option.label && (
                  <span className={styles.optionValue}>{option.value}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SelectDropdown;