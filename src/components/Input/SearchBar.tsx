import React from "react";
import { Search, X } from "lucide-react";
import BaseInput from './BaseInput';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  showClearButton?: boolean;
  width?: string | number;
  variant?: 'gray' | 'white'; // variant prop 추가
}

const SearchBar: React.FC<SearchBarProps> = ({ 
  value, 
  onChange, 
  placeholder = "검색어를 입력하세요",
  showClearButton = true,
  variant = 'gray'
}) => {
  return (
    <BaseInput
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      leftIcon={<Search />}
      rightIcon={showClearButton && value ? <X /> : undefined}
      onRightIconClick={showClearButton && value ? () => onChange("") : undefined}
      className="Body"
      variant={variant}
    />
  );
};

export default SearchBar;