import React from "react";
import BaseInput from '../Input/BaseInput';

interface InputWithIconProps extends Omit<React.ComponentProps<typeof BaseInput>, 'leftIcon'> {
  icon: React.ReactNode;
}

const InputWithIcon: React.FC<InputWithIconProps> = ({ 
  icon,
  variant = 'white',
  className = 'Body',
  leftIconSize = 'small',
  ...rest
}) => {
  return (
    <BaseInput
      leftIcon={icon}
      variant={variant}
      className={className}
      leftIconSize={leftIconSize}
      {...rest}
    />
  );
};

export default InputWithIcon;