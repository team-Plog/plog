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
import type {OpenApiSpec, ApiTestConfig} from "../../assets/mockProjectData";
import {deleteProject, getProjectDetail} from "../../api";
import ApiTree from "../../components/ApiTree/ApiTree";
import WarningModal from "../../components/warningModal/warningModal";

interface ProjectData {
  id: number;
  title: string;
  summary: string;
  description: string;
}

interface ApiServer {
  id: string;
  name: string;
  groups: {
    id: string;
    name: string;
    endpoints: {
      id: string;
      path: string;
      method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
    }[];
  }[];
}

const ProjectDetail: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const projectId = location.state?.projectId;
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [openApiSpecs, setOpenApiSpecs] = useState<OpenApiSpec[]>([]);
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [testGoal, setTestGoal] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [apiTestConfigs, setApiTestConfigs] = useState<ApiTestConfig[]>([]);
  const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);

  useEffect(() => {
    if (!projectId) {
      navigate("/");
      return;
    }

    getProjectDetail(projectId)
      .then((res) => {
        const data = res.data.data;
        setProjectData({
          id: data.id,
          title: data.title,
          summary: data.summary,
          description: data.description,
        });
        setOpenApiSpecs(data.openapi_specs);
      })
      .catch((err) => {
        console.error("❌ 프로젝트 상세 불러오기 실패:", err);
        navigate("/");
      });
  }, [projectId, navigate]);

  const convertToApiTreeData = (specs: OpenApiSpec[]): ApiServer[] => {
    return specs.map((spec) => ({
      id: spec.id.toString(),
      name: spec.title, // "MedEasy API", "Payment API" 등
      groups: spec.tags.map((tag) => ({
        id: tag.id.toString(),
        name: tag.name, // "인증 관리", "복약 관리" 등
        endpoints: tag.endpoints.map((endpoint) => ({
          id: endpoint.id.toString(),
          path: endpoint.path,
          method: endpoint.method,
        })),
      })),
    }));
  };

  const refreshProjectData = async () => {
    try {
      const res = await getProjectDetail(projectId);
      const data = res.data.data;
      setProjectData({
        id: data.id,
        title: data.title,
        summary: data.summary,
        description: data.description,
      });
      setOpenApiSpecs(data.openapi_specs);
      console.log("✅ 프로젝트 데이터 새로고침 완료");
    } catch (err) {
      console.error("❌ 프로젝트 데이터 새로고침 실패:", err);
    }
  };

  // API 테스트 설정 카드 추가
  const handleAddApiTest = (endpoint: string) => {
    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint: endpoint,
    };
    setApiTestConfigs((prev) => [...prev, newConfig]);
  };

  const handleEndpointClick = (
    endpoint: {id: string; path: string; method: string},
    serverName: string,
    groupName: string
  ) => {
    console.log(`선택된 엔드포인트:`, {
      server: serverName,
      group: groupName,
      path: endpoint.path,
      method: endpoint.method,
    });

    // 기존 handleAddApiTest와 동일한 로직으로 API 테스트 설정 추가
    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint: endpoint.path,
    };
    setApiTestConfigs((prev) => [...prev, newConfig]);
  };

  // API 테스트 설정 카드 제거
  const handleRemoveApiTest = (id: string) => {
    setApiTestConfigs((prev) => prev.filter((config) => config.id !== id));
  };

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
      {isModalOpen && (
        <UrlModal
          onClose={() => setIsModalOpen(false)}
          projectId={projectData.id}
          onSuccess={refreshProjectData}
        />
      )}
      <Header />
      <div className={styles.mainContent}>
        {/* 왼쪽 영역 */}
        <div className={styles.leftSection}>
          <div className={styles.scrollArea}>
            {openApiSpecs.length > 0 ? (
              <ApiTree
                servers={convertToApiTreeData(openApiSpecs)}
                onEndpointClick={handleEndpointClick}
              />
            ) : (
              <div className={styles.noApiData}>
                <p>등록된 API가 없습니다.</p>
                <p>API 서버를 등록해주세요.</p>
              </div>
            )}
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
                  {isWarningModalOpen && (
                    <WarningModal
                      projectId={projectData.id}
                      onClose={() => setIsWarningModalOpen(false)}
                      onSuccess={async () => {
                        await deleteProject(projectData.id);
                        console.log("✅ 삭제 완료");
                        navigate("/");
                      }}
                    />
                  )}
                  {menuOpen && (
                    <ActionMenu
                      projectId={projectData.id}
                      onEdit={() => setMenuOpen(false)}
                      onDelete={() => {
                        setMenuOpen(false);
                        setIsWarningModalOpen(true);
                      }}
                      onClose={() => setMenuOpen(false)}
                    />
                  )}
                </div>
                <div className={`Body ${styles.projectSubtitle}`}>
                  {projectData.summary}
                </div>
              </div>
              <div className={`CaptionLight ${styles.projectDescription}`}>
                {projectData.description}
              </div>
            </div>

            <div className={styles.divider}></div>

            <div className={styles.apiGroupsSection}>
              {openApiSpecs.length > 0 ? (
                // 각 OpenAPI 스펙의 tags를 순회하며 ApiGroupCard 렌더링
                openApiSpecs.flatMap((spec) =>
                  spec.tags.map((tag) => (
                    <ApiGroupCard
                      key={`${spec.id}-${tag.id}`}
                      groupName={tag.name}
                      baseUrl={spec.base_url}
                      endpoints={tag.endpoints}
                      onAddEndpoint={handleAddApiTest}
                    />
                  ))
                )
              ) : (
                <div className={styles.noApiGroups}>
                  <p>등록된 API 그룹이 없습니다.</p>
                  <p>
                    상단의 "API 서버 등록" 버튼을 클릭하여 API를 추가해보세요.
                  </p>
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
