import React from "react";
import { X } from "lucide-react";
import BaseInput from './BaseInput';

interface InputFieldProps {
  title?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  showClearButton?: boolean;
  width?: string | number;
  variant?: 'gray' | 'white';
}

const InputField: React.FC<InputFieldProps> = ({ 
  title, 
  placeholder, 
  value, 
  onChange,
  showClearButton = true,
  variant = 'white'
}) => {
  return (
    <BaseInput
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      title={title}
      rightIcon={showClearButton && value ? <X /> : undefined}
      onRightIconClick={showClearButton && value ? () => onChange("") : undefined}
      variant={variant}
    />
  );
};

export default InputField;