import React, {useState} from "react";
import styles from "./UrlModal.module.css";
import {InputField} from "../Input";
import {Button} from "../Button/Button";
import EndPoint from "../../assets/images/endPoint.svg";

interface UrlModalProps {
  onClose: () => void;
}

const UrlModal: React.FC<UrlModalProps> = ({onClose}) => {
  const [projectName, setProjectName] = useState("");
  const [projectSummary, setProjectSummary] = useState("");
  const [projectDescription, setProjectDescription] = useState("");

  const handleSave = () => {
    console.log("저장하기");
    onClose();
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.container}>
          <div className={styles.imageContainer}>
            <img src={EndPoint} className={styles.image} />
          </div>
          <div className={styles.inputContainer}>
            <InputField
              title="API 문서 URL"
              placeholder="예: https://example.com/api-docs"
              value={projectName}
              onChange={setProjectName}
            />

            <div className={styles.buttonGroup}>
              <Button variant="secondary" onClick={onClose}>
                취소
              </Button>
              <Button variant="primaryGradient" onClick={handleSave}>
                추가하기
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UrlModal;
