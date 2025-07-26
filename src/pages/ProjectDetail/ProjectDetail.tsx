import React, {useState, useEffect} from "react";
import {useLocation, useNavigate} from "react-router-dom";
import {InputField} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./ProjectDetail.module.css";
import {MoreHorizontal, Play, Plus, Save} from "lucide-react";
import UrlModal from "../../components/UrlModal/UrlModal";
import ActionMenu from "../../components/ActionMenu/ActionMenu";
import {getProjectById} from "../../assets/mockProjectData";
import type {ProjectData} from "../../assets/mockProjectData";

const ProjectDetail: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const projectId = location.state?.projectId;
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    console.log("ProjectDetail useEffect - projectId:", projectId);
    if (projectId) {
      const project = getProjectById(projectId);
      console.log("Found project:", project);
      if (project) {
        setProjectData(project);
      } else {
        console.log("Project not found, redirecting to home");
        // 프로젝트를 찾을 수 없으면 홈으로 리다이렉트
        navigate("/");
      }
    } else {
      console.log("No projectId provided");
      navigate("/");
    }
  }, [projectId, navigate]);

  // 프로젝트 데이터가 로드되지 않았으면 로딩 상태 표시
  if (!projectData) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.mainContent}>
          <div style={{padding: "20px", textAlign: "center"}}>
            프로젝트를 불러오는 중...
          </div>
        </div>
      </div>
    );
  }

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
              <div className={styles.projectTitle}>
                <div className="HeadingS">{projectData.title}</div>
                <button
                  className={styles.menuButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(!menuOpen);
                  }}
                  aria-label="프로젝트 메뉴"
                  type="button">
                  <MoreHorizontal />
                </button>
                {menuOpen && (
                  <ActionMenu
                    onEdit={() => {
                      setMenuOpen(false);
                    }}
                    onDelete={() => {
                      setMenuOpen(false);
                    }}
                    onClose={() => setMenuOpen(false)}
                  />
                )}
              </div>
              <div className={`Body ${styles.projectSubtitle}`}>
                {projectData.description}
              </div>
            </div>
            <div className={`CaptionLight ${styles.projectDescription}`}>
              {projectData.detailedDescription}
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