import React from "react";
import styles from "./Header.module.css";
import "../../assets/styles/typography.css";
import {ChevronLeft, ChevronRight, Moon} from "lucide-react";

const Header: React.FC = () => {
  const goBack = () => window.history.back();
  const goForward = () => window.history.forward();
  return (
    <div className={styles.header}>
      <div className={styles.title}>
        <div className={styles.filledCircle} />
        <div className="HeadingS">PLog</div>
        <div className={styles.button}>
          <ChevronLeft onClick={goBack}/>
          <ChevronRight onClick={goForward}/>
        </div>
      </div>
      <div className={styles.moonIcon}>
        <Moon />
      </div>
    </div>
  );
};

export default Header;
