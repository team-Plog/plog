import React, {useState, useEffect} from "react";
import {useLocation, useNavigate} from "react-router-dom";
import {InputField} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./ProjectDetail.module.css";
import {MoreHorizontal, Play, Plus, Save} from "lucide-react";
import UrlModal from "../../components/UrlModal/UrlModal";
import ActionMenu from "../../components/ActionMenu/ActionMenu";
import ApiGroupCard from "../../components/ApiGroupCard/ApiGroupCard";
import ApiTestConfigCard from "../../components/ApiTestConfigCard/ApiTestConfigCard";
import {getProjectById, getApiGroupsByProjectId} from "../../assets/mockProjectData";
import type {ProjectData, ApiGroup} from "../../assets/mockProjectData";

interface ApiTestConfig {
  id: string;
  endpoint: string;
}

const ProjectDetail: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const projectId = location.state?.projectId;
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [apiGroups, setApiGroups] = useState<ApiGroup[]>([]);
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [testGoal, setTestGoal] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [apiTestConfigs, setApiTestConfigs] = useState<ApiTestConfig[]>([]);

  useEffect(() => {
    console.log("ProjectDetail useEffect - projectId:", projectId);
    if (projectId) {
      const project = getProjectById(projectId);
      console.log("Found project:", project);
      if (project) {
        setProjectData(project);
        // 프로젝트에 해당하는 API 그룹 데이터 로드
        const projectApiGroups = getApiGroupsByProjectId(projectId);
        setApiGroups(projectApiGroups);
        console.log("Loaded API groups:", projectApiGroups);
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

  // API 테스트 설정 카드 추가
  const handleAddApiTest = (endpoint: string) => {
    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint: endpoint
    };
    setApiTestConfigs(prev => [...prev, newConfig]);
  };

  // API 테스트 설정 카드 제거
  const handleRemoveApiTest = (id: string) => {
    setApiTestConfigs(prev => prev.filter(config => config.id !== id));
  };

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
          <div className={styles.scrollArea}>
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
            
            <div className={styles.divider}></div>
            
            <div className={styles.apiGroupsSection}>
              {apiGroups.length > 0 ? (
                apiGroups.map((group, index) => (
                  <ApiGroupCard
                    key={index}
                    groupName={group.groupName}
                    baseUrl={group.baseUrl}
                    endpoints={group.endpoints}
                    onAddEndpoint={handleAddApiTest}
                  />
                ))
              ) : (
                <div className={styles.noApiGroups}>
                  <p>등록된 API 그룹이 없습니다.</p>
                  <p>상단의 "API 서버 등록" 버튼을 클릭하여 API를 추가해보세요.</p>
                </div>
              )}
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
              <InputField
                title="테스트 목표"
                placeholder="테스트 목표를 입력하세요."
                value={testGoal}
                onChange={setTestGoal}
              />
              
              {/* API 테스트 설정 카드들 */}
              {apiTestConfigs.map((config) => (
                <ApiTestConfigCard
                  key={config.id}
                  endpoint={config.endpoint}
                  onRemove={() => handleRemoveApiTest(config.id)}
                />
              ))}
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