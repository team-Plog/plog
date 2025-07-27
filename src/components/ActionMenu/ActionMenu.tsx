import React, {useEffect, useRef} from "react";
import styles from "./ActionMenu.module.css";
import {Pen, Trash} from "lucide-react";

interface ActionMenuProps {
  projectId: number;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onClose: () => void;
}

const ActionMenu: React.FC<ActionMenuProps> = ({
  projectId,
  onEdit,
  onDelete,
  onClose,
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

  return (
    <div className={styles.dropdown} ref={menuRef}>
      <button onClick={() => onEdit(projectId)} className={styles.item}>
        <Pen />
        <span className="Body">편집</span>
      </button>
      <button onClick={() => onDelete(projectId)} className={styles.item}>
        <Trash />
        <span className="Body">삭제</span>
      </button>
    </div>
  );
};

export default ActionMenu;
