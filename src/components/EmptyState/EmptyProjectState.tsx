import React from "react";
import { CirclePlus } from "lucide-react";
import styles from "./EmptyProjectState.module.css";

interface EmptyProjectStateProps {
  title?: string;
  description?: string;
}

const EmptyProjectState: React.FC<EmptyProjectStateProps> = ({
  title = "아직 생성된 프로젝트가 없습니다.",
  description = "부하 테스트를 시작하려면 새로운 프로젝트를 생성하세요."
}) => {
  return (
    <div className={styles.emptyState}>
      {/* Icon Container */}
      <div className={styles.emptyIconContainer}>
        <CirclePlus className={styles.emptyIcon} />
      </div>

      {/* Text Content */}
      <div className={styles.emptyTextContent}>
        <p className={`HeadingS ${styles.emptyTitle}`}>
          {title}
        </p>
        <p className={`Body ${styles.emptyDescription}`}>
          {description}
        </p>
      </div>
    </div>
  );
};

export default EmptyProjectState;