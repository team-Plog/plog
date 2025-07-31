import React, {useState} from "react";
import {
  Link,
  X,
  Clock,
  UserRound,
  LockKeyhole,
  ChartLine,
  Plus,
  Minus,
} from "lucide-react";
import {InputWithIcon} from "../../components/Input";
import ToggleButton from "../../components/Button/ToggleButton";
import styles from "./ApiTestConfigCard.module.css";

interface ApiTestConfigCardProps {
  endpoint: string;
  onRemove: () => void;
}

const ApiTestConfigCard: React.FC<ApiTestConfigCardProps> = ({
  endpoint,
  onRemove,
}) => {
  const [waitTime, setWaitTime] = useState("1ms");
  const [userControlMethod, setUserControlMethod] = useState<
    "fixed" | "gradual"
  >("fixed");
  const [userCount, setUserCount] = useState("1000");
  const [testTime, setTestTime] = useState("1ms");
  const [gradualSteps, setGradualSteps] = useState([
    {userCount: "1000", testTime: "1ms"},
  ]);

  const addGradualStep = () => {
    setGradualSteps([...gradualSteps, {userCount: "1000", testTime: "1ms"}]);
  };

  const removeGradualStep = (index: number) => {
    if (gradualSteps.length > 1) {
      setGradualSteps(gradualSteps.filter((_, i) => i !== index));
    }
  };

  const updateGradualStep = (
    index: number,
    field: "userCount" | "testTime",
    value: string
  ) => {
    const newSteps = [...gradualSteps];
    newSteps[index][field] = value;
    setGradualSteps(newSteps);
  };

  return (
    <div className={styles.container}>
      {/* 첫 번째 영역 - 헤더 */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Link className={styles.linkIcon} />
          <span className={`${styles.endpoint} TitleL`}>{endpoint}</span>
        </div>
        <button
          className={styles.removeButton}
          onClick={onRemove}
          type="button">
          <X />
        </button>
      </div>

      {/* 두 번째 영역 - 설정 */}
      <div className={styles.configSection}>
        {/* 가상 사용자 대기 시간 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            가상 사용자 대기 시간
          </span>
          <InputWithIcon
            icon={<Clock />}
            value={waitTime}
            onChange={setWaitTime}
          />
        </div>

        {/* 사용자 수 조절 방식 */}
        <div className={styles.configItem}>
          <span className={`${styles.configLabel} CaptionBold`}>
            사용자 수 조절 방식
          </span>
          <ToggleButton
            options={[
              {value: "fixed", label: "고정", icon: <LockKeyhole />},
              {value: "gradual", label: "점진적 증가", icon: <ChartLine />},
            ]}
            selectedValue={userControlMethod}
            onChange={(value) =>
              setUserControlMethod(value as "fixed" | "gradual")
            }
          />
        </div>

        {/* 가상 사용자 수 & 테스트 시간 */}
        {userControlMethod === "fixed" ? (
          <div className={styles.horizontalGroup}>
            <div className={styles.configItem}>
              <span className={`${styles.configLabel} CaptionBold`}>
                가상 사용자 수
              </span>
              <InputWithIcon
                icon={<UserRound />}
                value={userCount}
                onChange={setUserCount}
              />
            </div>
            <div className={styles.configItem}>
              <span className={`${styles.configLabel} CaptionBold`}>
                테스트 시간
              </span>
              <InputWithIcon
                icon={<Clock />}
                value={testTime}
                onChange={setTestTime}
              />
            </div>
          </div>
        ) : (
          <div className={styles.gradualSection}>
            <div className={styles.horizontalGroup}>
              <div className={styles.configItem}>
                <span className={`${styles.configLabel} CaptionBold`}>
                  가상 사용자 수
                </span>
              </div>
              <div className={styles.configItem}>
                <div className={styles.labelWithButton}>
                  <span className={`${styles.configLabel} CaptionBold`}>
                    테스트 시간
                  </span>
                  <button
                    className={styles.addButton}
                    onClick={addGradualStep}
                    type="button">
                    <Plus />
                  </button>
                </div>
              </div>
            </div>

            {gradualSteps.map((step, index) => (
              <div key={index} className={styles.gradualStep}>
                <div className={styles.horizontalGroup}>
                  <div className={styles.configItem}>
                    <InputWithIcon
                      icon={<UserRound />}
                      value={step.userCount}
                      onChange={(value) =>
                        updateGradualStep(index, "userCount", value)
                      }
                    />
                  </div>
                  <div className={styles.configItem}>
                    <div className={styles.inputWithButton}>
                      <InputWithIcon
                        icon={<Clock />}
                        value={step.testTime}
                        onChange={(value) =>
                          updateGradualStep(index, "testTime", value)
                        }
                      />
                      {gradualSteps.length > 1 && (
                        <button
                          className={styles.removeStepButton}
                          onClick={() => removeGradualStep(index)}
                          type="button">
                          <Minus />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ApiTestConfigCard;
