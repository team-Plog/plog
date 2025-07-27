import React from "react";
import { X } from "lucide-react";
import BaseInput from './BaseInput';

interface InputFieldProps extends Omit<React.ComponentProps<typeof BaseInput>, 'rightIcon' | 'onRightIconClick'> {
  showClearButton?: boolean;
  onClear?: () => void;
}

const InputField: React.FC<InputFieldProps> = ({ 
  value, 
  onChange,
  showClearButton = true,
  onClear,
  variant = 'white',
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
      rightIcon={showClearButton && value ? <X /> : undefined}
      onRightIconClick={showClearButton && value ? handleClear : undefined}
      variant={variant}
      {...rest}
    />
  );
};

export default InputField;