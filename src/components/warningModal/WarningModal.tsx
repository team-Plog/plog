import React from "react";
import styles from "./WarningModal.module.css";
import {Button} from "../Button/Button";

interface WarningModalProps {
  onClose: () => void;
  projectId: number;
  onSuccess?: () => void;
}

const WarningModal: React.FC<WarningModalProps> = ({
  onClose,
  projectId,
  onSuccess,
}) => {
  const handleConfirm = async () => {
    try {
      if (onSuccess) {
        await onSuccess();
      }
      onClose();
    } catch (err) {
      console.error("❌ 삭제 실패:", err);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* 이미지 영역 */}
        <div className={styles.imageSection}>
          <div className={styles.imageContainer}></div>
        </div>

        {/* 입력 영역 */}
        <div className={styles.contentSection}>
          <div className={styles.warningContainer}>
            <div className={styles.warningText}>
              <div className={`${styles.warningTitle} TitleL`}>프로젝트를 정말 삭제할까요?</div>
              <div className={`${styles.warningSubTitle} Body`}>
                연결된 API 정보, 테스트 결과, 시나리오, 보고서 정보가 영구적으로
                삭제됩니다. 삭제된 프로젝트는 복구할 수 없습니다.
              </div>
            </div>
            <div className={styles.buttonGroup}>
              <Button variant="secondary" onClick={onClose}>
                취소
              </Button>
              <Button variant="primaryGradient" onClick={handleConfirm}>
                확인
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WarningModal;
