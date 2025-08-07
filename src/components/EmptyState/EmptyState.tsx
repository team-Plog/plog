import React from "react";
import { CirclePlus } from "lucide-react";
import styles from "./EmptyState.module.css";

type EmptyStateType = "project" | "test" | "history" | "custom";

interface EmptyStateProps {
  type?: EmptyStateType;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  type = "custom",
  title,
  description,
  icon
}) => {
  // 타입별 기본 설정
  const getDefaultContent = () => {
    switch (type) {
      case "project":
        return {
          title: "아직 생성된 프로젝트가 없습니다.",
          description: "부하 테스트를 시작하려면 새로운 프로젝트를 생성하세요.",
          icon: <CirclePlus className={styles.emptyIcon} />
        };
      case "test":
        return {
          title: "이 프로젝트에 등록된 테스트가 없습니다.",
          description: "API를 선택해 부하테스트를 시작해보세요.",
          icon: <CirclePlus className={styles.emptyIcon} />
        };
      default:
        return {
          title: "데이터가 없습니다.",
          description: "표시할 내용이 없습니다.",
          icon: <CirclePlus className={styles.emptyIcon} />
        };
    }
  };

  const defaultContent = getDefaultContent();

  return (
    <div className={`${styles.emptyState} ${type === 'project' ? styles.projectType : ''}`}>
      {/* Icon Container */}
      <div className={styles.emptyIconContainer}>
        {icon || defaultContent.icon}
      </div>

      {/* Text Content */}
      <div className={styles.emptyTextContent}>
        <p className={`HeadingS ${styles.emptyTitle}`}>
          {title || defaultContent.title}
        </p>
        <p className={`Body ${styles.emptyDescription}`}>
          {description || defaultContent.description}
        </p>
      </div>
    </div>
  );
};

export default EmptyState;