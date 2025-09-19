import React, {useState, useEffect, useRef, useCallback} from "react";
import {useLocation, useNavigate} from "react-router-dom";
import {InputField} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import Header from "../../components/Header/Header";
import styles from "./ProjectDetail.module.css";
import {
  MoreHorizontal,
  Play,
  Plus,
  Save,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import UrlModal from "../../components/UrlModal/UrlModal";
import ActionMenu from "../../components/ActionMenu/ActionMenu";
import ApiGroupCard from "../../components/ApiGroupCard/ApiGroupCard";
import ApiTestConfigCard, {
  type ApiTestConfig,
} from "../../components/ApiTestConfigCard/ApiTestConfigCard";
import type {OpenApiSpec} from "../../assets/mockProjectData";
import {
  deleteProject,
  getProjectDetail,
  generateLoadTestScript,
  deleteOpenAPI,
  deleteEndpoint,
} from "../../api";
import ApiTree from "../../components/ApiTree/ApiTree";
import WarningModal from "../../components/WarningModal/WarningModal";
import {type HttpMethod} from "../../components/Tag/types";

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
      method: HttpMethod;
    }[];
  }[];
}

// 임시 저장 데이터 타입 정의
interface TempSaveData {
  scenarioTitle: string;
  scenarioDescription: string;
  targetTps: string;
  apiTestConfigs: ApiTestConfig[];
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
  const [isSaving, setIsSaving] = useState(false);

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

  // 임시 저장 키 생성
  const getTempSaveKey = (projectId: number) =>
    `temp_save_project_${projectId}`;

  // 임시 저장된 데이터 불러오기
  const loadTempSaveData = useCallback((projectId: number) => {
    try {
      const key = getTempSaveKey(projectId);
      const savedData = localStorage.getItem(key);
      if (savedData) {
        const parsedData: TempSaveData = JSON.parse(savedData);
        setScenarioTitle(parsedData.scenarioTitle || "");
        setScenarioDescription(parsedData.scenarioDescription || "");
        setTargetTps(parsedData.targetTps || "");
        setApiTestConfigs(parsedData.apiTestConfigs || []);
        console.log("✅ 임시 저장된 데이터 복원 완료:", parsedData);
        return true;
      }
    } catch (error) {
      console.error("❌ 임시 저장 데이터 불러오기 실패:", error);
    }
    return false;
  }, []);

  // 임시 저장 함수
  const handleTempSave = async () => {
    if (!projectId) return;

    setIsSaving(true);
    try {
      const tempData: TempSaveData = {
        scenarioTitle,
        scenarioDescription,
        targetTps,
        apiTestConfigs,
      };

      const key = getTempSaveKey(projectId);
      localStorage.setItem(key, JSON.stringify(tempData));
      console.log("💾 임시 저장 완료:", tempData);

      // 사용자에게 피드백 제공
      alert("입력된 데이터가 임시 저장되었습니다.");
    } catch (error) {
      console.error("❌ 임시 저장 실패:", error);
      alert("임시 저장에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setIsSaving(false);
    }
  };

  // 임시 저장 데이터 삭제 (테스트 실행 시)
  const clearTempSaveData = useCallback((projectId: number) => {
    try {
      const key = getTempSaveKey(projectId);
      localStorage.removeItem(key);
      console.log("🗑️ 임시 저장 데이터 삭제 완료");
    } catch (error) {
      console.error("❌ 임시 저장 데이터 삭제 실패:", error);
    }
  }, []);

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

        // 프로젝트 데이터 로딩 후 임시 저장된 데이터 복원
        loadTempSaveData(data.id);
      })
      .catch((err) => {
        console.error("❌ 프로젝트 상세 불러오기 실패:", err);
        navigate("/");
      });
  }, [projectId, navigate, loadTempSaveData]);

  // 리사이즈 핸들러
  const handleMouseDown = useCallback(
    (side: "left" | "right") => (e: React.MouseEvent) => {
      e.preventDefault();
      if (side === "left") {
        setIsLeftResizing(true);
      } else {
        setIsRightResizing(true);
      }
    },
    []
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const mouseX = e.clientX - containerRect.left;

      if (isLeftResizing) {
        const newLeftWidth = (mouseX / containerWidth) * 100;

        if (newLeftWidth < COLLAPSE_THRESHOLD) {
          setIsLeftCollapsed(true);
          setLeftWidth(MIN_PANEL_WIDTH);
        } else if (
          newLeftWidth >= MIN_PANEL_WIDTH &&
          newLeftWidth <= MAX_PANEL_WIDTH
        ) {
          setLeftWidth(newLeftWidth);
          setIsLeftCollapsed(false);
        }
      }

      if (isRightResizing) {
        const newRightWidth =
          ((containerWidth - mouseX) / containerWidth) * 100;

        if (newRightWidth < COLLAPSE_THRESHOLD) {
          setIsRightCollapsed(true);
          setRightWidth(MIN_PANEL_WIDTH);
        } else if (
          newRightWidth >= MIN_PANEL_WIDTH &&
          newRightWidth <= MAX_PANEL_WIDTH
        ) {
          setRightWidth(newRightWidth);
          setIsRightCollapsed(false);
        }
      }
    },
    [isLeftResizing, isRightResizing]
  );

  const handleMouseUp = useCallback(() => {
    setIsLeftResizing(false);
    setIsRightResizing(false);
  }, []);

  useEffect(() => {
    if (isLeftResizing || isRightResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
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
      openapi_spec_id: spec.id,
      groups: spec.tags.map((tag) => ({
        id: tag.id.toString(),
        name: tag.name,
        endpoints: tag.endpoints.map((endpoint) => ({
          id: endpoint.id.toString(),
          path: endpoint.path,
          method: endpoint.method as HttpMethod,
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

  const buildDefaultFromSchema = (schema: any): any => {
    if (!schema) return null;

    // OpenAPI-like로 value에 감싼 형태 지원
    if (schema.value) return buildDefaultFromSchema(schema.value);

    // 타입이 명시되지 않은 경우, 구조로 추론
    const inferredType =
      schema.type ??
      (schema.properties ? "object" : schema.items ? "array" : undefined);

    const t = inferredType;

    // enum만 존재하면 첫 값 사용
    if (!t && Array.isArray(schema.enum) && schema.enum.length > 0) {
      return schema.enum[0];
    }

    switch (t) {
      case "object": {
        const obj: Record<string, any> = {};
        const props = schema.properties ?? {};
        const keys = Object.keys(props);
        for (const key of keys) {
          obj[key] = buildDefaultFromSchema(props[key]);
        }
        return obj;
      }
      case "array": {
        // 배열 example이 이미 배열 형태라면 그대로 반환
        if (Array.isArray(schema.example)) {
          return schema.example;
        }

        // 문자열 예제를 배열로 파싱 시도
        if (typeof schema.example === "string" && schema.example.trim()) {
          // 1. JSON 파싱 시도 (예: "[1,2,3]", '["a","b","c"]' 등)
          try {
            const parsed = JSON.parse(schema.example);
            if (Array.isArray(parsed)) {
              return parsed;
            }
          } catch {
            // JSON 파싱 실패 시 콤마 분리로 시도
          }

          // 2. 콤마로 분리하여 배열 생성 (예: "1,2,3", "a,b,c" 등)
          const parts = schema.example
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean);

          if (parts.length > 0) {
            const itemType = schema.items?.type;

            // 타입에 따라 적절히 변환
            const coerce = (x: string) => {
              if (itemType === "integer" || itemType === "number") {
                const num = Number(x);
                return Number.isFinite(num) ? num : x; // 숫자 변환 실패 시 원본 문자열 유지
              }
              if (itemType === "boolean") {
                return x.toLowerCase() === "true";
              }
              return x;
            };

            return parts.map(coerce);
          }
        }

        // example이 없거나 파싱에 실패한 경우, items 스키마로 기본 배열 생성
        const items = schema.items ?? {};
        return [buildDefaultFromSchema(items)];
      }
      case "integer":
      case "number":
        if (schema.example !== undefined) {
          const n = Number(schema.example);
          return Number.isFinite(n) ? n : 0;
        }
        return 0;
      case "boolean":
        if (schema.example !== undefined) {
          if (typeof schema.example === "boolean") return schema.example;
          if (typeof schema.example === "string")
            return schema.example.toLowerCase() === "true";
        }
        return false;
      case "string":
      default:
        // 예제가 있고 배열 타입이 아닌 경우에만 사용
        if (schema.example !== undefined) {
          return schema.example;
        }
        // 날짜/시간 포맷이라도 예제 우선, 없으면 빈 문자열
        return "";
    }
  };

  // endpoint.parameters에서 requestBody 스키마를 찾아 JSON 문자열 생성
  const getDefaultRequestBodyFromEndpoint = (endpoint: any): string => {
    if (!endpoint?.parameters) return "";

    const bodyParam = endpoint.parameters.find(
      (p: any) => p.param_type === "requestBody"
    );
    if (!bodyParam) return "";

    const schemaRoot = bodyParam.value; // object 또는 array(또는 value 래핑)
    const defaultObj = buildDefaultFromSchema(schemaRoot);

    try {
      return JSON.stringify(defaultObj, null, 2);
    } catch {
      return "";
    }
  };

  // path + method로 정확히 endpoint 원본 객체 찾기
  const findEndpointByPathAndMethod = (
    specs: OpenApiSpec[],
    path: string,
    method: string
  ): any | null => {
    for (const spec of specs) {
      for (const tag of spec.tags ?? []) {
        for (const ep of tag.endpoints ?? []) {
          if (
            ep.path === path &&
            (ep.method ?? "").toUpperCase() === method.toUpperCase()
          ) {
            return ep;
          }
        }
      }
    }
    return null;
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

  // OpenAPI Spec ID를 찾는 헬퍼 함수
  const findOpenApiSpecId = (serverId: string): number | null => {
    const spec = openApiSpecs.find((spec) => spec.id.toString() === serverId);
    return spec ? spec.id : null;
  };

  const handleEndpointClick = (
    endpoint: {id: string; path: string; method: string},
    serverName: string,
    groupName: string
  ) => {
    const method = endpoint.method as HttpMethod;

    // 🔎 원본 endpoint 객체를 path+method로 정확히 찾기
    const endpointObj = findEndpointByPathAndMethod(
      openApiSpecs,
      endpoint.path,
      method
    );
    if (!endpointObj) {
      console.error("엔드포인트를 찾을 수 없습니다:", endpoint.path, method);
      return;
    }

    // ✅ ID도 원본에서 정확히
    const endpointId = endpointObj.id;

    // ✅ 기본 요청 본문 생성 (POST/PUT/PATCH/DELETE 모두 지원)
    const needsBody = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    const defaultBody = needsBody
      ? getDefaultRequestBodyFromEndpoint(endpointObj)
      : "";

    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint_id: endpointId,
      endpoint_path: endpoint.path,
      method,
      scenario_name: `${groupName}_${endpoint.method}_${endpoint.path
        .split("/")
        .pop()}`,
      think_time: 1,
      executor: "constant-vus",
      stages: [{duration: "10s", target: 10}],
      parameters: needsBody
        ? [{name: "requestBody", param_type: "requestBody", value: defaultBody}]
        : [],
      headers: [{header_key: "", header_value: ""}],
    };
    setApiTestConfigs((prev) => [...prev, newConfig]);
  };

  // 서버(OpenAPI Spec) 삭제 핸들러
  const handleDeleteServer = async (serverId: string) => {
    try {
      const openApiSpecId = findOpenApiSpecId(serverId);
      if (!openApiSpecId) {
        console.error("OpenAPI Spec ID를 찾을 수 없습니다:", serverId);
        alert("삭제할 수 없습니다. 서버 정보를 찾을 수 없습니다.");
        return;
      }

      console.log("🗑️ 서버 삭제 중:", openApiSpecId);
      await deleteOpenAPI(openApiSpecId);
      console.log("✅ 서버 삭제 완료");

      // 프로젝트 데이터 새로고침
      await refreshProjectData();
      alert("서버가 성공적으로 삭제되었습니다.");
    } catch (error) {
      console.error("❌ 서버 삭제 실패:", error);
      alert("서버 삭제에 실패했습니다. 다시 시도해주세요.");
    }
  };

  // 그룹 삭제 핸들러 (그룹 내 모든 엔드포인트 삭제)
  const handleDeleteGroup = async (
    serverId: string,
    groupId: string,
    endpointIds: string[]
  ) => {
    try {
      console.log("🗑️ 그룹 삭제 중:", {serverId, groupId, endpointIds});

      // 그룹 내 모든 엔드포인트를 순차적으로 삭제
      for (const endpointId of endpointIds) {
        await deleteEndpoint(parseInt(endpointId));
        console.log(`✅ 엔드포인트 삭제 완료: ${endpointId}`);
      }

      console.log("✅ 그룹 내 모든 엔드포인트 삭제 완료");

      // 프로젝트 데이터 새로고침
      await refreshProjectData();
      alert("그룹이 성공적으로 삭제되었습니다.");
    } catch (error) {
      console.error("❌ 그룹 삭제 실패:", error);
      alert("그룹 삭제에 실패했습니다. 다시 시도해주세요.");
    }
  };

  // 엔드포인트 삭제 핸들러
  const handleDeleteEndpoint = async (endpointId: string) => {
    try {
      console.log("🗑️ 엔드포인트 삭제 중:", endpointId);
      await deleteEndpoint(parseInt(endpointId));
      console.log("✅ 엔드포인트 삭제 완료");

      // 프로젝트 데이터 새로고침
      await refreshProjectData();
      alert("엔드포인트가 성공적으로 삭제되었습니다.");
    } catch (error) {
      console.error("❌ 엔드포인트 삭제 실패:", error);
      alert("엔드포인트 삭제에 실패했습니다. 다시 시도해주세요.");
    }
  };

  const handleAddApiTest = (
    endpointPath: string,
    method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH"
  ) => {
    // 🔎 원본 endpoint 객체를 path+method로 정확히 찾기
    const endpointObj = findEndpointByPathAndMethod(
      openApiSpecs,
      endpointPath,
      method
    );
    if (!endpointObj) {
      console.error("엔드포인트를 찾을 수 없습니다:", endpointPath, method);
      return;
    }

    // ✅ ID도 원본에서 정확히
    const endpointId = endpointObj.id;

    // ✅ 기본 요청 본문 생성 (POST/PUT/PATCH/DELETE 모두 지원)
    const needsBody = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    const defaultBody = needsBody
      ? getDefaultRequestBodyFromEndpoint(endpointObj)
      : "";

    const newConfig: ApiTestConfig = {
      id: Date.now().toString(),
      endpoint_id: endpointId,
      endpoint_path: endpointPath,
      method, // 그대로
      scenario_name: `scenario_${Date.now()}`,
      think_time: 1,
      executor: "constant-vus",
      stages: [{duration: "10s", target: 10}],
      parameters: needsBody
        ? [{name: "requestBody", param_type: "requestBody", value: defaultBody}]
        : [],
      headers: [{header_key: "", header_value: ""}],
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
    // 입력값 검증
    if (!scenarioTitle.trim()) {
      alert("테스트 시나리오 제목을 입력해주세요.");
      return;
    }

    if (apiTestConfigs.length === 0) {
      alert("최소 1개 이상의 API 테스트를 구성해주세요.");
      return;
    }

    // duration 형식 검증
    const durationRegex = /^\d+[smh]$/;
    const invalidDurations: string[] = [];

    for (const config of apiTestConfigs) {
      for (const stage of config.stages) {
        if (!durationRegex.test(stage.duration)) {
          invalidDurations.push(
            `${config.endpoint_path}의 테스트 시간 "${stage.duration}"`
          );
        }
      }
    }

    if (invalidDurations.length > 0) {
      alert(
        `다음 테스트 시간 형식이 올바르지 않습니다:\n${invalidDurations.join(
          "\n"
        )}\n\n올바른 형식: 숫자 + 단위 (예: 10s, 5m, 1h)`
      );
      return;
    }

    setIsSubmitting(true);

    try {
      // 새로운 API 요청 형식에 맞게 데이터 구성
      const loadTestRequest = {
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
          // 새로 추가된 필드들
          parameters:
            config.parameters
              ?.filter((p) => p.name && p.value)
              .map((p) => ({
                name: p.name,
                param_type: p.param_type,
                value: p.value,
              })) || [],
          headers:
            config.headers
              ?.filter((h) => h.header_key && h.header_value)
              .map((h) => ({
                header_key: h.header_key,
                header_value: h.header_value,
              })) || [],
        })),
      };

      console.log("🚀 로드 테스트 요청:", loadTestRequest);

      const response = await generateLoadTestScript(loadTestRequest);
      console.log("✅ 로드 테스트 시작:", response.data);

      // 테스트 실행 성공 시 임시 저장 데이터 삭제
      clearTempSaveData(projectId);

      // 테스트 페이지로 이동하면서 job_name을 전달
      navigate("/test", {
        state: {
          projectId,
          projectTitle: projectData?.title,
          jobName: response.data.data.job_name,
          fileName: response.data.data.file_name,
          testTitle: scenarioTitle,
        },
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
  const centerWidth =
    100 -
    (isLeftCollapsed ? 0 : leftWidth) -
    (isRightCollapsed ? 0 : rightWidth);

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
          className={`${styles.leftSection} ${
            isLeftCollapsed ? styles.collapsed : ""
          }`}
          style={{
            width: isLeftCollapsed ? "0px" : `${leftWidth}%`,
            minWidth: isLeftCollapsed ? "0px" : `${leftWidth}%`,
            maxWidth: isLeftCollapsed ? "0px" : `${leftWidth}%`,
          }}>
          <div className={styles.scrollArea}>
            {openApiSpecs.length > 0 ? (
              <ApiTree
                servers={convertToApiTreeData(openApiSpecs)}
                onEndpointClick={handleEndpointClick}
                onDeleteServer={handleDeleteServer}
                onDeleteGroup={handleDeleteGroup}
                onDeleteEndpoint={handleDeleteEndpoint}
                onVersionChanged={refreshProjectData}
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
              onClick={() => setIsModalOpen(true)}
              responsive={true}>
              API 서버 등록
            </Button>
          </div>
        </div>

        {/* 왼쪽 리사이저 */}
        {!isLeftCollapsed && (
          <div
            className={`${styles.resizer} ${
              isLeftResizing ? styles.active : ""
            }`}
            onMouseDown={handleMouseDown("left")}
          />
        )}

        {/* 접힌 왼쪽 패널 토글 버튼 */}
        {isLeftCollapsed && (
          <button
            className={`${styles.collapsedToggle} ${styles.leftCollapsedToggle}`}
            onClick={toggleLeftPanel}
            type="button">
            <ChevronRight />
          </button>
        )}

        {/* 가운데 영역 */}
        <div
          className={styles.centerSection}
          style={{width: `${centerWidth}%`}}>
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
            type="button">
            <ChevronLeft />
          </button>
        )}

        {/* 오른쪽 리사이저 */}
        {!isRightCollapsed && (
          <div
            className={`${styles.resizer} ${
              isRightResizing ? styles.active : ""
            }`}
            onMouseDown={handleMouseDown("right")}
          />
        )}

        {/* 오른쪽 영역 */}
        <div
          className={`${styles.rightSection} ${
            isRightCollapsed ? styles.collapsed : ""
          }`}
          style={{
            width: isRightCollapsed ? "0px" : `${rightWidth}%`,
            minWidth: isRightCollapsed ? "0px" : `${rightWidth}%`,
            maxWidth: isRightCollapsed ? "0px" : `${rightWidth}%`,
          }}>
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
            <Button
              variant="secondary"
              icon={<Save />}
              onClick={handleTempSave}
              disabled={isSaving}
              responsive={true}>
              {isSaving ? "저장 중..." : "임시 저장"}
            </Button>
            <Button
              variant="primaryGradient"
              icon={<Play />}
              onClick={handleRunLoadTest}
              disabled={isSubmitting}
              responsive={true}>
              {isSubmitting ? "테스트 시작 중..." : "테스트 실행하기"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetail;
