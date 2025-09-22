import React, {useEffect, useRef} from "react";
import styles from "./ActionMenu.module.css";
import {Pen, Trash, RefreshCw} from "lucide-react";

interface ActionMenuProps {
  projectId: number;
  onEdit?: (id: number) => void;
  onDelete: (id: number) => void;
  onVersionChange?: (id: number) => void;
  onClose: () => void;
  deleteOnly?: boolean; // 삭제만 표시할지 여부
  showVersionChange?: boolean; // 버전 변경 메뉴 표시 여부
  position?: { x: number; y: number }; // 커스텀 위치
}

const ActionMenu: React.FC<ActionMenuProps> = ({
  projectId,
  onEdit,
  onDelete,
  onVersionChange,
  onClose,
  deleteOnly = false,
  showVersionChange = false,
  position,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const menuStyle = position ? {
    position: 'fixed' as const,
    left: position.x,
    top: position.y,
    right: 'auto',
  } : {};

  return (
    <div 
      className={`${styles.dropdown} ${deleteOnly && !showVersionChange ? styles.deleteOnlyMenu : ''}`} 
      ref={menuRef}
      style={menuStyle}>
      
      {showVersionChange && onVersionChange && (
        <button onClick={() => onVersionChange(projectId)} className={styles.item}>
          <RefreshCw />
          <span className={`Body ${styles.text}`}>버전 변경</span>
        </button>
      )}
      
      {!deleteOnly && onEdit && (
        <button onClick={() => onEdit(projectId)} className={styles.item}>
          <Pen />
          <span className={`Body ${styles.text}`}>편집</span>
        </button>
      )}
      
      <button 
        onClick={() => onDelete(projectId)} 
        className={`${styles.item} ${deleteOnly && !showVersionChange ? styles.singleItem : ''}`}>
        <Trash />
        <span className={`Body ${styles.text}`}>삭제</span>
      </button>
    </div>
  );
};

export default ActionMenu;