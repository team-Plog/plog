import React, {useState} from "react";
import styles from "./MainModal.module.css";

import ProjectCard1 from "../../assets/images/projectCard1.svg";
import ProjectCard2 from "../../assets/images/projectCard2.svg";
import ProjectCard3 from "../../assets/images/projectCard3.svg";
import InputField from "../InputField/InputField";
import {Button} from "../Button/Button";

interface MainModalProps {
  onClose: () => void;
}

const MainModal: React.FC<MainModalProps> = ({onClose}) => {
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
        <div className={styles.imageContainer}>
          <img src={ProjectCard1} className={styles.card1} />
          <img src={ProjectCard2} className={styles.card2} />
          <img src={ProjectCard3} className={styles.card3} />
        </div>
        <div className={styles.container}>
          <div className={styles.inputContainer}>
            <InputField
              title="프로젝트 제목"
              placeholder="프로젝트 이름을 입력하세요."
              value={projectName}
              onChange={setProjectName}
            />

            <InputField
              title="프로젝트 요약"
              placeholder="프로젝트에 대한 간단한 설명을 입력하세요."
              value={projectSummary}
              onChange={setProjectSummary}
            />

            <InputField
              title="프로젝트 상세 내용"
              placeholder="프로젝트에 대한 상세 내용을 입력하세요."
              value={projectDescription}
              onChange={setProjectDescription}
            />

            <div className={styles.buttonGroup}>
              <Button variant="secondary" onClick={onClose}>
                취소
              </Button>
              <Button variant="primaryGradient" onClick={handleSave}>
                저장하기
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainModal;
