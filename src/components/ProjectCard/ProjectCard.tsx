import React, {useState} from "react";
import {MoreHorizontal} from "lucide-react";
import styles from "./ProjectCard.module.css";
import {StatusBadge} from "../Tag";
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

  const handleMenuClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    // 메뉴 클릭 로직 추가 예정
    console.log("Menu clicked for project:", id);
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
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}>
      <div className={styles.badgeRow}>
        <StatusBadge status={status ?? "before"} />
        <button
          className={styles.menuButton}
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen(!menuOpen);
          }}
          aria-label="프로젝트 메뉴">
          <MoreHorizontal
            style={{
              width: "var(--icon-size-sm)",
              height: "var(--icon-size-sm)",
              color: "var(--color-gray-200)",
            }}
          />
        </button>
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
