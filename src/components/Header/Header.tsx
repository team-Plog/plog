import React from "react";
import styles from "./Header.module.css";
import '../../assets/styles/typography.css'
import { Moon } from "lucide-react";

const Header: React.FC = () => {
  return (
    <div className={styles.header}>
      <div className="HeadingS">PLog</div>
      <div className={styles.moonIcon}>
        <Moon />
      </div>
    </div>
  );
};

export default Header;
