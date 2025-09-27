import React, { useState, type ReactNode } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import styles from "./ModeToggleDropdown.module.css";

export interface DropdownOption {
  id: string;
  label: string;
  icon?: ReactNode;
  value?: unknown;
}

interface ModeToggleDropdownProps {
  currentOption: DropdownOption;
  options: DropdownOption[];
  onSelect: (option: DropdownOption) => void;
  className?: string;
}

const ModeToggleDropdown: React.FC<ModeToggleDropdownProps> = ({
  currentOption,
  options,
  onSelect,
  className,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);

  const handleSelect = (option: DropdownOption) => {
    onSelect(option);
    setDropdownOpen(false);
  };

  const handleDropdownToggle = () => {
    setDropdownOpen((prev) => !prev);
  };

  // 현재 선택된 옵션을 제외한 나머지 옵션들
  const availableOptions = options.filter(option => option.id !== currentOption.id);

  return (
    <div className={`${styles.container} ${className || ''}`}>
      <div className={styles.toggleButton} onClick={handleDropdownToggle}>
        {currentOption.icon && (
          <div className={styles.icon}>
            {currentOption.icon}
          </div>
        )}
        <span className={`HeadingS ${styles.toggleText}`}>
          {currentOption.label}
        </span>
        <div className={`${styles.icon} ${styles.chevron}`}>
          {dropdownOpen ? <ChevronUp /> : <ChevronDown />}
        </div>
      </div>
      
      {dropdownOpen && availableOptions.length > 0 && (
        <div className={styles.dropdown}>
          {availableOptions.map((option) => (
            <button
              key={option.id}
              className={styles.dropdownButton}
              onClick={() => handleSelect(option)}
            >
              {option.icon && (
                <div className={styles.icon}>
                  {option.icon}
                </div>
              )}
              <span className={`HeadingS ${styles.dropdownText}`}>
                {option.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModeToggleDropdown;