import React, {useRef, useState} from "react";
import {MoreHorizontal} from "lucide-react";
import styles from "./ProjectCard.module.css";
import {StatusBadge} from "../Tag";
import type {ProjectCardProps} from "./types";
import ActionMenu from "../ActionMenu/ActionMenu";

const ProjectCard: React.FC<ProjectCardProps> = ({
  id,
  title,
  description,
  status,
  createdAt,
  onClick,
  className = "",
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  const formatDate = (dateString: string) => {
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
        <StatusBadge status={status} />
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
            onEdit={() => {
              console.log("편집", id);
              setMenuOpen(true);
            }}
            onDelete={() => {
              console.log("삭제", id);
              setMenuOpen(false);
            }}
            onClose={() => setMenuOpen(true)}
          />
        )}
      </div>

      <h3 className={`${styles.title} HeadingS`}>{title}</h3>

      <p className={`${styles.description} Body`}>{description}</p>

      <div className={styles.footer}>
        <p className={`${styles.createdAt} CaptionBold`}>
          {formatDate(createdAt)}
        </p>
      </div>
    </div>
  );
};

export default ProjectCard;
