import React, {useState, useEffect, useRef, useCallback} from "react";
import {useLocation, useNavigate} from "react-router-dom";
import {InputField} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./ProjectDetail.module.css";
import {MoreHorizontal, Play, Plus, Save, ChevronLeft, ChevronRight} from "lucide-react";
import UrlModal from "../../components/UrlModal/UrlModal";
import ActionMenu from "../../components/ActionMenu/ActionMenu";
import ApiGroupCard from "../../components/ApiGroupCard/ApiGroupCard";
import ApiTestConfigCard, {type ApiTestConfig} from "../../components/ApiTestConfigCard/ApiTestConfigCard";
import type {OpenApiSpec} from "../../assets/mockProjectData";
import {deleteProject, getProjectDetail} from "../../api";
import {generateLoadTestScript, type LoadTestingRequest} from "../../api/loadTesting";
import ApiTree from "../../components/ApiTree/ApiTree";
import WarningModal from "../../components/WarningModal/WarningModal";

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
  const [targetTps, setTargetTps] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [apiTestConfigs, setApiTestConfigs] = useState<ApiTestConfig[]>([]);
  const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 리사이즈 관련 상태
  const [leftWidth, setLeftWidth] = useState(20.1); // %
  const [rightWidth, setRightWidth] = useState(25.8); // %
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);
  const [isLeftResizing, setIsLeftResizing] = useState(false);
  const [isRightResizing, setIsRightResizing] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // 최소/최대 너비 설정 (%)
  const MIN_PANEL_WIDTH = 15;
  const MAX_PANEL_WIDTH = 40;
  const COLLAPSE_THRESHOLD = 12; // 이 너비 이하로 줄어들면 자동으로 접힘

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
        console.log("📩 프로젝트 상세 정보: ", data);
      })
      .catch((err) => {
        console.error("❌ 프로젝트 상세 불러오기 실패:", err);
        navigate("/");
      });
  }, [projectId, navigate]);

  // 리사이즈 핸들러
  const handleMouseDown = useCallback((side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    if (side === 'left') {
      setIsLeftResizing(true);
    } else {
      setIsRightResizing(true);
    }
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const mouseX = e.clientX - containerRect.left;

    if (isLeftResizing) {
      const newLeftWidth = (mouseX / containerWidth) * 100;
      
      if (newLeftWidth < COLLAPSE_THRESHOLD) {
        setIsLeftCollapsed(true);
        setLeftWidth(MIN_PANEL_WIDTH);
      } else if (newLeftWidth >= MIN_PANEL_WIDTH && newLeftWidth <= MAX_PANEL_WIDTH) {
        setLeftWidth(newLeftWidth);
        setIsLeftCollapsed(false);
      }
    }

    if (isRightResizing) {
      const newRightWidth = ((containerWidth - mouseX) / containerWidth) * 100;
      
      if (newRightWidth < COLLAPSE_THRESHOLD) {
        setIsRightCollapsed(true);
        setRightWidth(MIN_PANEL_WIDTH);
      } else if (newRightWidth >= MIN_PANEL_WIDTH && newRightWidth <= MAX_PANEL_WIDTH) {
        setRightWidth(newRightWidth);
        setIsRightCollapsed(false);
      }
    }
  }, [isLeftResizing, isRightResizing]);

  const handleMouseUp = useCallback(() => {
    setIsLeftResizing(false);
    setIsRightResizing(false);
  }, []);

  useEffect(() => {
    if (isLeftResizing || isRightResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isLeftResizing, isRightResizing, handleMouseMove, handleMouseUp]);

  // 패널 토글 함수
  const toggleLeftPanel = () => {
    setIsLeftCollapsed(!isLeftCollapsed);
  };

  const toggleRightPanel = () => {
    setIsRightCollapsed(!isRightCollapsed);
  };

  const convertToApiTreeData = (specs: OpenApiSpec[]): ApiServer[] => {
    return specs.map((spec) => ({
      id: spec.id.toString(),
      name: spec.title,
      groups: spec.tags.map((tag) => ({
        id: tag.id.toString(),
        name: tag.name,
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

  // endpoint_id를 찾는 헬퍼 함수
  const findEndpointId = (path: string): number | null => {
    for (const spec of openApiSpecs) {
      for (const tag of spec.tags) {
        for (const endpoint of tag.endpoints) {
          if (endpoint.path === path) {
            return endpoint.id;
          }
        }
      }
    }
    return null;
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

    const endpointId = findEndpointId(endpoint.path);
    if (!endpointId) {
      console.error("엔드포인트 ID를 찾을 수 없습니다:", endpoint.path);
      return;
    }

    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint_id: endpointId,
      endpoint_path: endpoint.path,
      scenario_name: `${groupName}_${endpoint.method}_${endpoint.path.split('/').pop()}`,
      think_time: 1,
      executor: 'constant-vus',
      stages: [{ duration: '10s', target: 10 }],
    };
    setApiTestConfigs((prev) => [...prev, newConfig]);
  };

  const handleAddApiTest = (endpoint: string) => {
    const endpointId = findEndpointId(endpoint);
    if (!endpointId) {
      console.error("엔드포인트 ID를 찾을 수 없습니다:", endpoint);
      return;
    }

    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint_id: endpointId,
      endpoint_path: endpoint,
      scenario_name: `scenario_${Date.now()}`,
      think_time: 1,
      executor: 'constant-vus',
      stages: [{ duration: '10s', target: 10 }],
    };
    setApiTestConfigs((prev) => [...prev, newConfig]);
  };

  const handleRemoveApiTest = (id: string) => {
    setApiTestConfigs((prev) => prev.filter((config) => config.id !== id));
  };

  const handleConfigChange = (updatedConfig: ApiTestConfig) => {
    setApiTestConfigs((prev) => 
      prev.map((config) => 
        config.id === updatedConfig.id ? updatedConfig : config
      )
    );
  };

  // 로드 테스팅 실행
  const handleRunLoadTest = async () => {
    if (apiTestConfigs.length === 0) {
      alert("최소 1개 이상의 API 테스트를 구성해주세요.");
      return;
    }

    if (!scenarioTitle.trim()) {
      alert("테스트 시나리오 제목을 입력해주세요.");
      return;
    }

    setIsSubmitting(true);

    try {
      const loadTestRequest: LoadTestingRequest = {
        title: scenarioTitle,
        description: scenarioDescription || "설명 없음",
        target_tps: targetTps ? parseFloat(targetTps) : undefined,
        scenarios: apiTestConfigs.map((config) => ({
          name: config.scenario_name,
          endpoint_id: config.endpoint_id,
          executor: config.executor,
          think_time: config.think_time,
          stages: config.stages,
          response_time_target: config.response_time_target,
          error_rate_target: config.error_rate_target,
        })),
      };

      console.log("🚀 로드 테스트 요청:", loadTestRequest);

      const response = await generateLoadTestScript(loadTestRequest);
      console.log("✅ 로드 테스트 시작:", response.data);

      // 테스트 페이지로 이동하면서 job_name을 전달
      navigate("/test", { 
        state: { 
          jobName: response.data.job_name,
          fileName: response.data.file_name,
          testTitle: scenarioTitle
        } 
      });
    } catch (error) {
      console.error("❌ 로드 테스트 시작 실패:", error);
      alert("로드 테스트 시작에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setIsSubmitting(false);
    }
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

  // 중앙 영역의 너비 계산
  const centerWidth = 100 - (isLeftCollapsed ? 0 : leftWidth) - (isRightCollapsed ? 0 : rightWidth);

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
      <div className={styles.mainContent} ref={containerRef}>
        {/* 왼쪽 영역 */}
        <div 
          className={`${styles.leftSection} ${isLeftCollapsed ? styles.collapsed : ''}`}
          style={{
            width: isLeftCollapsed ? '0px' : `${leftWidth}%`,
            minWidth: isLeftCollapsed ? '0px' : `${leftWidth}%`,
            maxWidth: isLeftCollapsed ? '0px' : `${leftWidth}%`,
          }}
        >
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

        {/* 왼쪽 리사이저 */}
        {!isLeftCollapsed && (
          <div 
            className={`${styles.resizer} ${isLeftResizing ? styles.active : ''}`}
            onMouseDown={handleMouseDown('left')}
          />
        )}

        {/* 접힌 왼쪽 패널 토글 버튼 */}
        {isLeftCollapsed && (
          <button 
            className={`${styles.collapsedToggle} ${styles.leftCollapsedToggle}`}
            onClick={toggleLeftPanel}
            type="button"
          >
            <ChevronRight />
          </button>
        )}

        {/* 가운데 영역 */}
        <div 
          className={styles.centerSection}
          style={{ width: `${centerWidth}%` }}
        >
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

        {/* 접힌 오른쪽 패널 토글 버튼 */}
        {isRightCollapsed && (
          <button 
            className={`${styles.collapsedToggle} ${styles.rightCollapsedToggle}`}
            onClick={toggleRightPanel}
            type="button"
          >
            <ChevronLeft />
          </button>
        )}

        {/* 오른쪽 리사이저 */}
        {!isRightCollapsed && (
          <div 
            className={`${styles.resizer} ${isRightResizing ? styles.active : ''}`}
            onMouseDown={handleMouseDown('right')}
          />
        )}

        {/* 오른쪽 영역 */}
        <div 
          className={`${styles.rightSection} ${isRightCollapsed ? styles.collapsed : ''}`}
          style={{
            width: isRightCollapsed ? '0px' : `${rightWidth}%`,
            minWidth: isRightCollapsed ? '0px' : `${rightWidth}%`,
            maxWidth: isRightCollapsed ? '0px' : `${rightWidth}%`,
          }}
        >
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
                title="목표 TPS (선택사항)"
                placeholder="예: 1000"
                value={targetTps}
                onChange={setTargetTps}
              />

              {apiTestConfigs.map((config) => (
                <ApiTestConfigCard
                  key={config.id}
                  config={config}
                  onRemove={() => handleRemoveApiTest(config.id)}
                  onChange={handleConfigChange}
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
              onClick={handleRunLoadTest}
              disabled={isSubmitting || apiTestConfigs.length === 0}>
              {isSubmitting ? "테스트 시작 중..." : "테스트 실행하기"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetail;