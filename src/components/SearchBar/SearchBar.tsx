import React from "react";
import { Search } from "lucide-react";
import styles from './SearchBar.module.css';

const SearchBar: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}> = ({ value, onChange, placeholder }) => {
  return (
    <div className={styles.searchContainer}>
      <Search className={styles.searchIcon} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || "입력 내용"}
        className={`${styles.searchInput} Body`}
      />
    </div>
  );
};

export default SearchBar;