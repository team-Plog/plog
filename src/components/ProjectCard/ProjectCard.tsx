import React, {useState} from "react";
import styles from "./ProjectCard.module.css";
import type {ProjectCardProps} from "./types";
import ActionMenu from "../ActionMenu/ActionMenu";
import {deleteProject} from "../../api";
import { useNavigate } from "react-router-dom";

const ProjectCard: React.FC<ProjectCardProps> = ({
  id,
  title,
  summary,
  status,
  updatedAt,
  onClick,
  className = "",
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleClick = () => {
    if (onClick) {
      onClick(id);
    }
  };

  // 우클릭 핸들러 추가
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault(); // 기본 브라우저 컨텍스트 메뉴 방지
    e.stopPropagation();
    setMenuOpen(!menuOpen);
    console.log("Right-click menu for project:", id);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "날짜 없음";
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}.${month}.${day}`;
  };

  return (
    <div
      className={`${styles.card} ${className}`}
      onClick={handleClick}
      onContextMenu={handleContextMenu} // 우클릭 이벤트 추가
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <div className={styles.badgeRow}>
        {menuOpen && (
          <ActionMenu
            projectId={id}
            onEdit={(projectId) => {
              console.log("편집", projectId);
              setMenuOpen(false);
            }}
            onDelete={(projectId) => {
              deleteProject(projectId)
                .then(() => {
                  console.log("삭제 성공:", projectId);
                  setMenuOpen(false);
                  navigate("/");
                })
                .catch((error) => {
                  console.error("삭제 실패:", error);
                });
            }}
            onClose={() => setMenuOpen(false)}
          />
        )}
      </div>
      <h3 className={`${styles.title} HeadingS`}>{title}</h3>
      <p className={`${styles.summary} Body`}>{summary}</p>
      <div className={styles.footer}>
        <p className={`${styles.updated_at} CaptionBold`}>
          {formatDate(updatedAt)}
        </p>
      </div>
    </div>
  );
};

export default ProjectCard;