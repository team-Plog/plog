import React from "react";
import {
  Link,
  X,
  Clock,
  UserRound,
  LockKeyhole,
  ChartLine,
  Plus,
  Minus,
  AlertTriangle,
  Target,
} from "lucide-react";
import {InputWithIcon} from "../../components/Input";
import ToggleButton from "../../components/Button/ToggleButton";
import styles from "./ApiTestConfigCard.module.css";

interface Stage {
  duration: string;
  target: number;
}

export interface ApiTestConfig {
  id: string;
  endpoint_id: number;
  endpoint_path: string;
  scenario_name: string;
  think_time: number;
  executor: 'constant-vus' | 'ramping-vus';
  response_time_target?: number;
  error_rate_target?: number;
  stages: Stage[];
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
  const updateConfig = (updates: Partial<ApiTestConfig>) => {
    onChange({ ...config, ...updates });
  };

  // 숫자만 입력받는 헬퍼 함수
  const handleNumberInput = (value: string): number => {
    // 빈 문자열이면 0 반환
    if (value === '') return 0;
    
    // 숫자만 허용 (소수점 포함)
    const numericValue = value.replace(/[^0-9.]/g, '');
    const parsedValue = parseFloat(numericValue);
    
    // NaN이면 0 반환, 그렇지 않으면 파싱된 값 반환
    return isNaN(parsedValue) ? 0 : parsedValue;
  };

  // 정수만 입력받는 헬퍼 함수
  const handleIntegerInput = (value: string): number => {
    // 빈 문자열이면 0 반환
    if (value === '') return 0;
    
    // 숫자만 허용 (정수만)
    const numericValue = value.replace(/[^0-9]/g, '');
    const parsedValue = parseInt(numericValue);
    
    // NaN이면 0 반환, 그렇지 않으면 파싱된 값 반환
    return isNaN(parsedValue) ? 0 : parsedValue;
  };

  const addStage = () => {
    const newStages = [...config.stages, { duration: "10s", target: 10 }];
    updateConfig({ stages: newStages });
  };

  const removeStage = (index: number) => {
    if (config.stages.length > 1) {
      const newStages = config.stages.filter((_, i) => i !== index);
      updateConfig({ stages: newStages });
    }
  };

  const updateStage = (index: number, field: keyof Stage, value: string | number) => {
    const newStages = [...config.stages];
    if (field === 'target') {
      newStages[index][field] = typeof value === 'string' ? handleIntegerInput(value) : value;
    } else {
      newStages[index][field] = value as string;
    }
    updateConfig({ stages: newStages });
  };

  // duration 입력값 필터링 (숫자, s, m, h만 허용)
  const handleDurationInput = (value: string): string => {
    // 숫자, s, m, h만 허용하고 나머지 문자는 제거
    return value.replace(/[^0-9smh]/g, '');
  };

  const handleDurationChange = (index: number, value: string) => {
    const filteredValue = handleDurationInput(value);
    updateStage(index, 'duration', filteredValue);
  };

  return (
    <div className={styles.container}>
      {/* 헤더 */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Link className={styles.linkIcon} />
          <span className={`${styles.endpoint} TitleL`}>{config.endpoint_path}</span>
        </div>
        <button
          className={styles.removeButton}
          onClick={onRemove}
          type="button">
          <X />
        </button>
      </div>

      {/* 설정 */}
      <div className={styles.configSection}>
        {/* 시나리오 이름 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            시나리오 이름
          </span>
          <InputWithIcon
            icon={<Target />}
            value={config.scenario_name}
            onChange={(value) => updateConfig({ scenario_name: value })}
            placeholder="시나리오 이름을 입력하세요"
          />
        </div>

        {/* 요청 간 대기시간 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            요청 간 대기시간 (초)
          </span>
          <InputWithIcon
            icon={<Clock />}
            value={config.think_time.toString()}
            onChange={(value) => updateConfig({ think_time: handleNumberInput(value) })}
            placeholder="1"
          />
        </div>

        {/* 응답시간 목표 (선택사항) */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            응답시간 목표 (ms, 선택사항)
          </span>
          <InputWithIcon
            icon={<Clock />}
            value={config.response_time_target?.toString() || ''}
            onChange={(value) => {
              if (value === '') {
                updateConfig({ response_time_target: undefined });
              } else {
                updateConfig({ response_time_target: handleNumberInput(value) });
              }
            }}
            placeholder="예: 100"
          />
        </div>

        {/* 에러율 목표 (선택사항) */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            에러율 목표 (%, 선택사항)
          </span>
          <InputWithIcon
            icon={<AlertTriangle />}
            value={config.error_rate_target?.toString() || ''}
            onChange={(value) => {
              if (value === '') {
                updateConfig({ error_rate_target: undefined });
              } else {
                updateConfig({ error_rate_target: handleNumberInput(value) });
              }
            }}
            placeholder="예: 5"
          />
        </div>

        {/* 실행 모드 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            실행 모드
          </span>
          <ToggleButton
            options={[
              {value: "constant-vus", label: "고정", icon: <LockKeyhole />},
              {value: "ramping-vus", label: "점진적 증가", icon: <ChartLine />},
            ]}
            selectedValue={config.executor}
            onChange={(value) => {
              const newExecutor = value as 'constant-vus' | 'ramping-vus';
              // 고정 모드로 변경할 때는 첫 번째 단계만 유지
              if (newExecutor === 'constant-vus' && config.stages.length > 1) {
                updateConfig({ 
                  executor: newExecutor,
                  stages: [config.stages[0]] // 첫 번째 단계만 유지
                });
              } else {
                updateConfig({ executor: newExecutor });
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
            {config.executor === 'ramping-vus' && (
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

          {(config.executor === 'constant-vus' ? [config.stages[0]] : config.stages).map((stage, index) => {
            // 고정 모드에서는 실제 인덱스를 0으로, 점진적 증가에서는 실제 인덱스 사용
            const actualIndex = config.executor === 'constant-vus' ? 0 : index;
            
            return (
              <div key={actualIndex} className={styles.stageItem}>
                <div className={styles.stageInputRow}>
                  <div className={styles.stageColumn}>
                    <InputWithIcon
                      icon={<UserRound />}
                      value={stage.target.toString()}
                      onChange={(value) => updateStage(actualIndex, 'target', value)}
                      placeholder="10"
                    />
                  </div>
                  <div className={styles.stageColumn}>
                    <InputWithIcon
                      icon={<Clock />}
                      value={stage.duration}
                      onChange={(value) => handleDurationChange(actualIndex, value)}
                      placeholder="10s (초: s, 분: m, 시: h)"
                    />
                  </div>
                  {config.executor === 'ramping-vus' && config.stages.length > 1 && (
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
    </div>
  );
};

export default ApiTestConfigCard;