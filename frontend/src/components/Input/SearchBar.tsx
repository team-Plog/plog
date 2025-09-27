import React from "react";
import { Search, X } from "lucide-react";
import BaseInput from './BaseInput';

interface SearchBarProps extends Omit<React.ComponentProps<typeof BaseInput>, 'leftIcon' | 'rightIcon' | 'onRightIconClick'> {
  placeholder?: string;
  showClearButton?: boolean;
  onClear?: () => void;
}

const SearchBar: React.FC<SearchBarProps> = ({ 
  value, 
  onChange, 
  placeholder = "검색어를 입력하세요",
  showClearButton = true,
  onClear,
  variant = 'gray',
  className = 'Body',
  ...rest
}) => {
  const handleClear = () => {
    onChange('');
    onClear?.();
  };

  return (
    <BaseInput
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      leftIcon={<Search />}
      rightIcon={showClearButton && value ? <X /> : undefined}
      onRightIconClick={showClearButton && value ? handleClear : undefined}
      variant={variant}
      className={className}
      {...rest}
    />
  );
};

export default SearchBar;