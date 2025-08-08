import React from "react";
import styles from "./ReportEditor.module.css";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import ReportViewer from "./ReportViewer";
import {InputField} from "../Input";

interface ReportEditorProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  onConfigChange: (config: ReportConfig) => void;
}

const ReportEditor: React.FC<ReportEditorProps> = ({
  reportData,
  reportConfig,
  onConfigChange,
}) => {
  const handleInputChange = (
    field: keyof ReportConfig,
    value: string | boolean
  ) => {
    onConfigChange({
      ...reportConfig,
      [field]: value,
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.editorPanel}>
        <div className={styles.formGroup}>
          <InputField
            title="보고서 제목"
            value={reportConfig.customTitle}
            onChange={(value) => handleInputChange("customTitle", value)}
            placeholder="리포트 제목을 입력하세요"
            showClearButton={true}
          />
        </div>

        <div className={styles.formGroup}>
          <InputField
            title="테스트 시나리오 상세 내용"
            value={reportConfig.customDescription}
            onChange={(value) => handleInputChange("customDescription", value)}
            placeholder="리포트 설명을 입력하세요"
            multiline
            showClearButton={true}
          />
        </div>
      </div>

      <div className={styles.previewPanel}>
        <ReportViewer
          reportData={reportData}
          reportConfig={reportConfig}
          isPreview={true}
        />
      </div>
    </div>
  );
};

export default ReportEditor;
