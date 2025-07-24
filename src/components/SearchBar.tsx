import React from "react";
import { Search } from "lucide-react";
import '../assets/styles/colors.css'
import { typography } from '../assets//styles/typography';

const SearchBar: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}> = ({ value, onChange, placeholder }) => {
  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <Search style={{
        position: 'absolute',
        left: '12px',
        top: '50%',
        transform: 'translateY(-50%)',
        color: 'var(--color-gray-200)',
        width: '16px',
        height: '16px'
      }} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || "입력 내용"}
        style={{
          width: '100%',
          paddingLeft: '36px',
          paddingRight: '12px',
          paddingTop: '10px',
          paddingBottom: '10px',
          backgroundColor: 'var(--color-gray-100)',
          border: 'none',
          borderRadius: '8px',
          color: 'var(--color-black)',
          outline: 'none',
          transition: 'all 0.2s',
          ...typography.Body
        }}
      />
    </div>
  );
};

export default SearchBar;
