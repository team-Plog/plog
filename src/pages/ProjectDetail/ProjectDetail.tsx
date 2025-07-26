import React, {useState} from "react";
import {InputField} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./ProjectDetail.module.css";
import {Play, Plus, Save} from "lucide-react";
import UrlModal from "../../components/UrlModal/UrlModal";
import {useNavigate} from "react-router-dom";

const ProjectDetail: React.FC = () => {
  const navigate = useNavigate();
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className={styles.container}>
      {isModalOpen && <UrlModal onClose={() => setIsModalOpen(false)} />}
      <Header />
      <div className={styles.mainContent}>
        {/* 왼쪽 영역 */}
        <div className={styles.leftSection}>
          <div className={styles.scrollArea}>
            {[...Array(40)].map((_, i) => (
              <div key={i}>왼쪽 스크롤 영역</div>
            ))}
          </div>
          <div className={styles.buttonContainer}>
            <Button
              variant="secondary"
              icon={<Plus />}
              onClick={() => setIsModalOpen(true)}>
              API 서버 등록
            </Button>
          </div>
        </div>

        {/* 가운데 영역 */}
        <div className={styles.centerSection}>
          <div className={styles.projectInfo}>
            <div className={styles.projectHeader}>
              <div className="HeadingS">MedEasy Project</div>
              <div className={`Body ${styles.projectSubtitle}`}>
                고령자 및 만성질환자를 위한 복약관리 자동화 테스트 프로젝트
              </div>
            </div>
            <div className={`CaptionLight ${styles.projectDescription}`}>
              MedEasy는 고령자 및 디지털 소외계층을 위한 복약 관리 플랫폼입니다.
              본 프로젝트는 MedEasy 시스템의 주요 API들에 대해 부하 테스트를
              수행하고, 로그인, 복약 등록, NFC 기반 체크, 보호자 알림 등 핵심
              기능의 안정성과 확장성을 검증하는 것을 목표로 합니다. 또한,
              OpenAPI를 통해 자동으로 API를 가져오고, 시나리오 기반 테스트
              구성이 가능하도록 설계되었습니다.
            </div>
          </div>
        </div>

        {/* 오른쪽 영역 */}
        <div className={styles.rightSection}>
          <div className={styles.formArea}>
            <div className={styles.inputContainer}>
              <InputField
                title="테스트 시나리오 제목"
                placeholder="시나리오 제목을 입력하세요."
                value={scenarioTitle}
                onChange={setScenarioTitle}
              />
              <InputField
                title="테스트 시나리오 상세 내용"
                placeholder="테스트 대상, API, 방식, 목적 등을 입력하세요."
                value={scenarioDescription}
                onChange={setScenarioDescription}
              />
            </div>
          </div>
          <div className={styles.buttonGroup}>
            <Button variant="secondary" icon={<Save />}>
              임시 저장
            </Button>
            <Button
              variant="primaryGradient"
              icon={<Play />}
              onClick={() => navigate("/test")}>
              테스트 실행하기
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetail;
