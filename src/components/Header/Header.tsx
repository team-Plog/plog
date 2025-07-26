import React from "react";
import styles from "./Header.module.css";
import "../../assets/styles/typography.css";
import {Circle, Moon} from "lucide-react";

const Header: React.FC = () => {
  return (
    <div className={styles.header}>
      <div className={styles.title}>
        <div className={styles.circleIcon}>
          <Circle />
        </div>
        <div className="HeadingS">PLog</div>
      </div>
      <div className={styles.moonIcon}>
        <Moon />
      </div>
    </div>
  );
};

export default Header;
