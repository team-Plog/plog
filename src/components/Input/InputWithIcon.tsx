import React from "react";
import BaseInput from '../Input/BaseInput';

interface InputWithIconProps {
  icon: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const InputWithIcon: React.FC<InputWithIconProps> = ({ 
  icon,
  value, 
  onChange, 
  placeholder 
}) => {
  return (
    <BaseInput
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      leftIcon={icon}
      variant="white"
      className="Body"
    />
  );
};

export default InputWithIcon;