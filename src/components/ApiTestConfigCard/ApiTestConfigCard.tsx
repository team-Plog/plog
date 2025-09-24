import React, {useState, useEffect} from "react";
import {
  X,
  Clock,
  UserRound,
  LockKeyhole,
  ChartLine,
  Plus,
  Minus,
  AlertTriangle,
  Target,
  Cog,
  Play,
  ChevronRight,
  ChevronUp,
  Key,
  ChartColumn,
} from "lucide-react";
import {InputWithIcon, InputField} from "../../components/Input";
import ToggleButton from "../../components/Button/ToggleButton";
import HttpMethodTag from "../../components/Tag/HttpMethodTag";
import SelectDropdown from "../../components/Dropdown/SelectDropdown";
import {type HttpMethod} from "../../components/Tag/types";
import styles from "./ApiTestConfigCard.module.css";

interface Stage {
  duration: string;
  target: number;
}

interface Parameter {
  name: string;
  param_type: "path" | "query" | "requestBody";
  value: string;
}

interface Header {
  header_key: string;
  header_value: string;
}

export interface ApiTestConfig {
  id: string;
  endpoint_id: number;
  endpoint_path: string;
  method: HttpMethod; // 전체 HttpMethod 타입 사용
  scenario_name: string;
  think_time: number;
  executor: "constant-vus" | "ramping-vus";
  response_time_target?: number;
  error_rate_target?: number;
  stages: Stage[];
  parameters?: Parameter[];
  headers?: Header[];
}

interface ApiTestConfigCardProps {
  config: ApiTestConfig;
  onRemove: () => void;
  onChange: (config: ApiTestConfig) => void;
}

const ApiTestConfigCard: React.FC<ApiTestConfigCardProps> = ({
  config,
  onRemove,
  onChange,
}) => {
  const [isRequestConfigOpen, setIsRequestConfigOpen] = useState(false);
  const [isExecutionConfigOpen, setIsExecutionConfigOpen] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);

  // 헤더 키 옵션들
  const headerKeyOptions = [
    {value: "Authorization", label: "Authorization"},
    {value: "Content-Type", label: "Content-Type"},
    {value: "Accept", label: "Accept"},
    {value: "User-Agent", label: "User-Agent"},
    {value: "Host", label: "Host"},
    {value: "Cache-Control", label: "Cache-Control"},
    {value: "Connection", label: "Connection"},
    {value: "X-Request-Id", label: "X-Request-Id"},
    {value: "X-Correlation-Id", label: "X-Correlation-Id"},
    {value: "X-API-Key", label: "X-API-Key"},
    {value: "X-Forwarded-For", label: "X-Forwarded-For"},
    {value: "X-Forwarded-Proto", label: "X-Forwarded-Proto"},
    {value: "X-Real-IP", label: "X-Real-IP"},
  ];

  // 초기 데이터 설정 - 메서드별 필요한 필드들 초기화
  useEffect(() => {
    // 이미 초기화되었다면 실행하지 않음
    if (isInitialized) return;

    let shouldUpdate = false;
    const updates: Partial<ApiTestConfig> = {};

    // 헤더 초기화 - 시연용 기본값 설정 (Authorization: Bearer 12345)
    const headers = config.headers || [];
    if (headers.length === 0) {
      updates.headers = [{header_key: "Authorization", header_value: "Bearer 12345"}];
      shouldUpdate = true;
    }

    // 시연용 기본값 설정
    if (config.think_time === 0 || config.think_time === undefined) {
      updates.think_time = 1;
      shouldUpdate = true;
    }

    if (!config.response_time_target) {
      updates.response_time_target = 1000;
      shouldUpdate = true;
    }

    if (config.error_rate_target === undefined) {
      updates.error_rate_target = 0;
      shouldUpdate = true;
    }

    if (!config.executor) {
      updates.executor = "constant-vus";
      shouldUpdate = true;
    }

    if (!config.stages || config.stages.length === 0) {
      updates.stages = [{duration: "60s", target: 400}];
      shouldUpdate = true;
    } else if (config.stages.length === 1 && (config.stages[0].duration === "10s" && config.stages[0].target === 10)) {
      // 기존 기본값을 시연용 값으로 교체
      updates.stages = [{duration: "60s", target: 400}];
      shouldUpdate = true;
    }

    // parameters 초기화
    const parameters = config.parameters || [];

    // GET 메서드의 경우
    if (config.method === "GET") {
      const hasPathParam = parameters.some((p) => p.param_type === "path");
      const hasQueryParam = parameters.some((p) => p.param_type === "query");

      if (!hasPathParam || !hasQueryParam) {
        const newParameters = [...parameters];
        if (!hasPathParam) {
          newParameters.push({name: "", param_type: "path", value: ""});
        }
        if (!hasQueryParam) {
          newParameters.push({name: "", param_type: "query", value: ""});
        }
        updates.parameters = newParameters;
        shouldUpdate = true;
      }
    }

    // POST, PUT, PATCH 메서드의 경우 requestBody 추가
    if (["POST", "PUT", "PATCH"].includes(config.method)) {
      const hasRequestBody = parameters.some(
        (p) => p.param_type === "requestBody"
      );
      if (!hasRequestBody) {
        const newParameters = [
          ...parameters,
          {name: "requestBody", param_type: "requestBody" as const, value: ""},
        ];
        updates.parameters = newParameters;
        shouldUpdate = true;
      }
    }

    // 변경사항이 있을 때만 업데이트
    if (shouldUpdate) {
      onChange({...config, ...updates});
    }

    setIsInitialized(true);
  }, [config.method, isInitialized]); // onChange를 의존성에서 제거

  const updateConfig = (updates: Partial<ApiTestConfig>) => {
    onChange({...config, ...updates});
  };

  // 숫자만 입력받는 헬퍼 함수
  const handleNumberInput = (value: string): number => {
    if (value === "") return 0;
    const numericValue = value.replace(/[^0-9.]/g, "");
    const parsedValue = parseFloat(numericValue);
    return isNaN(parsedValue) ? 0 : parsedValue;
  };

  // 정수만 입력받는 헬퍼 함수
  const handleIntegerInput = (value: string): number => {
    if (value === "") return 0;
    const numericValue = value.replace(/[^0-9]/g, "");
    const parsedValue = parseInt(numericValue);
    return isNaN(parsedValue) ? 0 : parsedValue;
  };

  const addStage = () => {
    const newStages = [...config.stages, {duration: "60s", target: 400}];
    updateConfig({stages: newStages});
  };

  const removeStage = (index: number) => {
    if (config.stages.length > 1) {
      const newStages = config.stages.filter((_, i) => i !== index);
      updateConfig({stages: newStages});
    }
  };

  const updateStage = (
    index: number,
    field: keyof Stage,
    value: string | number
  ) => {
    const newStages = [...config.stages];
    if (field === "target") {
      newStages[index][field] =
        typeof value === "string" ? handleIntegerInput(value) : value;
    } else {
      newStages[index][field] = value as string;
    }
    updateConfig({stages: newStages});
  };

  const handleDurationInput = (value: string): string => {
    return value.replace(/[^0-9smh]/g, "");
  };

  const handleDurationChange = (index: number, value: string) => {
    const filteredValue = handleDurationInput(value);
    updateStage(index, "duration", filteredValue);
  };

  // Header 관련 함수들
  const updateHeader = (index: number, field: keyof Header, value: string) => {
    const newHeaders = [...(config.headers || [])];
    // headers 배열 크기 확인 및 확장
    if (index >= newHeaders.length) {
      for (let i = newHeaders.length; i <= index; i++) {
        newHeaders.push({header_key: "", header_value: ""});
      }
    }
    newHeaders[index][field] = value;
    updateConfig({headers: newHeaders});
  };

  // Parameter 관련 함수들
  const updateParameter = <K extends keyof Parameter>(
    index: number,
    field: K,
    value: Parameter[K]
  ) => {
    const newParameters = [...(config.parameters || [])];
    newParameters[index][field] = value as Parameter[K];
    updateConfig({parameters: newParameters});
  };

  const renderRequestConfig = () => {
    if (!isRequestConfigOpen) return null;

    const method = config.method;
    const headers = config.headers || [];
    const parameters = config.parameters || [];

    return (
      <div className={styles.configContent}>
        {/* 헤더 설정 - 모든 메서드에 표시 */}
        <div className={styles.configItem}>
          <div className={styles.labelWithButton}>
            <span className={`${styles.configLabel} CaptionBold`}>헤더</span>
            <button
              type="button"
              onClick={() =>
                updateConfig({
                  headers: [...headers, {header_key: "", header_value: ""}],
                })
              }
              className={styles.addButton}>
              <Plus />
            </button>
          </div>
          {headers.map((header, index) => (
            <div key={index} className={styles.parameterRow}>
              <SelectDropdown
                options={headerKeyOptions}
                value={header.header_key}
                onChange={(value) => updateHeader(index, "header_key", value)}
                placeholder="Key"
                icon={<Key />}
              />
              <InputWithIcon
                icon={<ChartColumn />}
                value={header.header_value}
                onChange={(value) => updateHeader(index, "header_value", value)}
                placeholder="Value"
              />

              {headers.length > 1 && (
                <div className={styles.headerButtons}>
                  <button
                    type="button"
                    onClick={() => {
                      const newHeaders = headers.filter((_, i) => i !== index);
                      updateConfig({headers: newHeaders});
                    }}
                    className={styles.removeButton}>
                    <Minus />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* GET 메서드인 경우 */}
        {method === "GET" && (
          <>
            {/* 경로 변수 */}
            <div className={styles.configItem}>
              <span className={`${styles.configLabel} CaptionBold`}>
                경로 변수
              </span>
              <div className={styles.parameterRow}>
                <InputWithIcon
                  icon={<Key />}
                  value={
                    parameters.find((p) => p.param_type === "path")?.name || ""
                  }
                  onChange={(value) => {
                    const index = parameters.findIndex(
                      (p) => p.param_type === "path"
                    );
                    if (index >= 0) {
                      updateParameter(index, "name", value);
                    }
                  }}
                  placeholder="Path"
                />
                <InputWithIcon
                  icon={<ChartColumn />}
                  value={
                    parameters.find((p) => p.param_type === "path")?.value || ""
                  }
                  onChange={(value) => {
                    const index = parameters.findIndex(
                      (p) => p.param_type === "path"
                    );
                    if (index >= 0) {
                      updateParameter(index, "value", value);
                    }
                  }}
                  placeholder="Value"
                />
              </div>
            </div>

            {/* 쿼리 파라미터 */}
            <div className={styles.configItem}>
              <span className={`${styles.configLabel} CaptionBold`}>
                쿼리 파라미터
              </span>
              {parameters
                .filter((p) => p.param_type === "query")
                .map((param, index) => (
                  <div key={index} className={styles.parameterRow}>
                    <InputWithIcon
                      icon={<Key />}
                      value={param.name}
                      onChange={(value) =>
                        updateParameter(index, "name", value)
                      }
                      placeholder="Param"
                    />
                    <InputWithIcon
                      icon={<ChartColumn />}
                      value={param.value}
                      onChange={(value) =>
                        updateParameter(index, "value", value)
                      }
                      placeholder="Value"
                    />
                  </div>
                ))}
            </div>
          </>
        )}

        {/* POST, PUT, PATCH 메서드인 경우 */}
        {["POST", "PUT", "PATCH"].includes(method) && (
          <div className={styles.configItem}>
            <span className={`${styles.configLabel} CaptionBold`}>
              요청 본문
            </span>
            <InputField
              placeholder="JSON 형식의 요청 본문을 입력하세요"
              value={
                parameters.find((p) => p.param_type === "requestBody")?.value ||
                ""
              }
              onChange={(value) => {
                const existingIndex = parameters.findIndex(
                  (p) => p.param_type === "requestBody"
                );
                if (existingIndex >= 0) {
                  updateParameter(existingIndex, "value", value);
                } else {
                  const newParameters = [
                    ...parameters,
                    {
                      name: "requestBody",
                      param_type: "requestBody" as const,
                      value,
                    },
                  ];
                  updateConfig({parameters: newParameters});
                }
              }}
              multiline
            />
          </div>
        )}
      </div>
    );
  };

  const renderExecutionConfig = () => {
    if (!isExecutionConfigOpen) return null;

    return (
      <div className={styles.configContent}>
        {/* 시나리오 이름 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            시나리오 이름
          </span>
          <InputWithIcon
            icon={<Target />}
            value={config.scenario_name}
            onChange={(value) => updateConfig({scenario_name: value})}
            placeholder="시나리오 이름을 입력하세요"
          />
        </div>

        {/* 요청 간 대기시간 & 응답시간 목표 */}
        <div className={styles.horizontalGroup}>
          <div className={styles.configItem}>
            <span className={`${styles.configLabel} CaptionBold`}>
              요청 간 대기시간 (초)
            </span>
            <InputWithIcon
              icon={<Clock />}
              value={config.think_time.toString()}
              onChange={(value) =>
                updateConfig({think_time: handleNumberInput(value)})
              }
              placeholder="1"
            />
          </div>
          <div className={styles.configItem}>
            <span className={`${styles.configLabel} CaptionBold`}>
              응답시간 목표 (ms, 선택)
            </span>
            <InputWithIcon
              icon={<Clock />}
              value={config.response_time_target?.toString() || ""}
              onChange={(value) => {
                if (value === "") {
                  updateConfig({response_time_target: undefined});
                } else {
                  updateConfig({
                    response_time_target: handleNumberInput(value),
                  });
                }
              }}
              placeholder="예: 100"
            />
          </div>
        </div>

        {/* 에러율 목표 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            에러율 목표 (%, 선택)
          </span>
          <InputWithIcon
            icon={<AlertTriangle />}
            value={config.error_rate_target?.toString() || ""}
            onChange={(value) => {
              if (value === "") {
                updateConfig({error_rate_target: undefined});
              } else {
                updateConfig({error_rate_target: handleNumberInput(value)});
              }
            }}
            placeholder="예: 5"
          />
        </div>

        {/* 실행 모드 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            사용자 수 조절 방식
          </span>
          <ToggleButton
            options={[
              {value: "constant-vus", label: "고정", icon: <LockKeyhole />},
              {value: "ramping-vus", label: "점진적 증가", icon: <ChartLine />},
            ]}
            selectedValue={config.executor}
            onChange={(value) => {
              const newExecutor = value as "constant-vus" | "ramping-vus";
              if (newExecutor === "constant-vus" && config.stages.length > 1) {
                updateConfig({
                  executor: newExecutor,
                  stages: [config.stages[0]],
                });
              } else {
                updateConfig({executor: newExecutor});
              }
            }}
          />
        </div>

        {/* 단계별 설정 */}
        <div className={styles.stagesSection}>
          <div className={styles.stagesHeader}>
            <div className={styles.stageColumn}>
              <span className={`${styles.configLabel} CaptionBold`}>
                가상 사용자 수
              </span>
            </div>
            <div className={styles.stageColumn}>
              <span className={`${styles.configLabel} CaptionBold`}>
                테스트 시간
              </span>
            </div>
            {config.executor === "ramping-vus" && (
              <div className={styles.stageButtonColumn}>
                <button
                  className={styles.addButton}
                  onClick={addStage}
                  type="button">
                  <Plus />
                </button>
              </div>
            )}
          </div>

          {(config.executor === "constant-vus"
            ? [config.stages[0]]
            : config.stages
          ).map((stage, index) => {
            const actualIndex = config.executor === "constant-vus" ? 0 : index;

            return (
              <div key={actualIndex} className={styles.stageItem}>
                <div className={styles.stageInputRow}>
                  <div className={styles.stageColumn}>
                    <InputWithIcon
                      icon={<UserRound />}
                      value={stage.target.toString()}
                      onChange={(value) =>
                        updateStage(actualIndex, "target", value)
                      }
                      placeholder="10"
                    />
                  </div>
                  <div className={styles.stageColumn}>
                    <InputWithIcon
                      icon={<Clock />}
                      value={stage.duration}
                      onChange={(value) =>
                        handleDurationChange(actualIndex, value)
                      }
                      placeholder="10s (초: s, 분: m, 시: h)"
                    />
                  </div>
                  {config.executor === "ramping-vus" &&
                    config.stages.length > 1 && (
                      <div className={styles.stageButtonColumn}>
                        <button
                          className={styles.removeStepButton}
                          onClick={() => removeStage(actualIndex)}
                          type="button">
                          <Minus />
                        </button>
                      </div>
                    )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className={styles.container}>
      {/* 헤더 */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <HttpMethodTag method={config.method} />
          <span className={`${styles.endpoint} TitleL`}>
            {config.endpoint_path}
          </span>
        </div>
        <button
          className={styles.removeButton}
          onClick={onRemove}
          type="button">
          <X />
        </button>
      </div>

      {/* 요청 설정 섹션 */}
      <div className={styles.configSection}>
        <button
          className={`${styles.toggleButton} ${
            isRequestConfigOpen ? styles.toggleButtonOpen : ""
          }`}
          onClick={() => setIsRequestConfigOpen(!isRequestConfigOpen)}
          type="button">
          <div className={styles.toggleLeft}>
            <Cog className={styles.toggleIcon} />
            <span className={`${styles.toggleTitle} TitleS`}>요청 설정</span>
          </div>
          {isRequestConfigOpen ? (
            <ChevronUp className={styles.chevronIcon} />
          ) : (
            <ChevronRight className={styles.chevronIcon} />
          )}
        </button>
        {renderRequestConfig()}
      </div>

      {/* 실행 파라미터 섹션 */}
      <div className={styles.configSection}>
        <button
          className={`${styles.toggleButton} ${
            isExecutionConfigOpen ? styles.toggleButtonOpen : ""
          }`}
          onClick={() => setIsExecutionConfigOpen(!isExecutionConfigOpen)}
          type="button">
          <div className={styles.toggleLeft}>
            <Play className={styles.toggleIcon} />
            <span className={`${styles.toggleTitle} TitleS`}>
              실행 파라미터
            </span>
          </div>
          {isExecutionConfigOpen ? (
            <ChevronUp className={styles.chevronIcon} />
          ) : (
            <ChevronRight className={styles.chevronIcon} />
          )}
        </button>
        {renderExecutionConfig()}
      </div>
    </div>
  );
};

export default ApiTestConfigCard;