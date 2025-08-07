import React from "react";
import styles from "./ReportEditor.module.css";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import ReportViewer from "./ReportViewer";
import { InputField } from "../Input";

interface ReportEditorProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  onConfigChange: (config: ReportConfig) => void;
}

const ReportEditor: React.FC<ReportEditorProps> = ({
  reportData,
  reportConfig,
  onConfigChange
}) => {
  const handleInputChange = (field: keyof ReportConfig, value: string | boolean) => {
    onConfigChange({
      ...reportConfig,
      [field]: value
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.editorPanel}>
        <h3 className={styles.sectionTitle}>리포트 설정</h3>
        
        <div className={styles.formGroup}>
          <label className={styles.label}>리포트 제목</label>
          <InputField
            value={reportConfig.customTitle}
            onChange={(value) => handleInputChange("customTitle", value)}
            placeholder="리포트 제목을 입력하세요"
            showClearButton={true}
          />
        </div>

        <div className={styles.formGroup}>
          <InputField
            title="리포트 설명"
            value={reportConfig.customDescription}
            onChange={(value) => handleInputChange("customDescription", value)}
            placeholder="리포트 설명을 입력하세요"
            multiline
            showClearButton={true}
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>회사명</label>
          <InputField
            value={reportConfig.companyName}
            onChange={(value) => handleInputChange("companyName", value)}
            placeholder="회사명을 입력하세요"
            showClearButton={true}
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>작성자</label>
          <InputField
            value={reportConfig.reporterName}
            onChange={(value) => handleInputChange("reporterName", value)}
            placeholder="작성자명을 입력하세요"
            showClearButton={true}
          />
        </div>

        <h4 className={styles.subsectionTitle}>포함할 섹션</h4>

        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={reportConfig.includeExecutiveSummary}
              onChange={(e) => handleInputChange("includeExecutiveSummary", e.target.checked)}
            />
            요약 정보
          </label>
        </div>

        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={reportConfig.includeDetailedMetrics}
              onChange={(e) => handleInputChange("includeDetailedMetrics", e.target.checked)}
            />
            상세 메트릭
          </label>
        </div>

        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={reportConfig.includeScenarioBreakdown}
              onChange={(e) => handleInputChange("includeScenarioBreakdown", e.target.checked)}
            />
            시나리오 분석
          </label>
        </div>

        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={reportConfig.includeCharts}
              onChange={(e) => handleInputChange("includeCharts", e.target.checked)}
            />
            차트 포함
          </label>
        </div>
      </div>

      <div className={styles.previewPanel}>
        <h3 className={styles.sectionTitle}>미리보기</h3>
        <div className={styles.previewContent}>
          <ReportViewer
            reportData={reportData}
            reportConfig={reportConfig}
            isPreview={true}
          />
        </div>
      </div>
    </div>
  );
};

export default ReportEditor;