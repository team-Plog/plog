import React, {useState} from "react";
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
  const [selectedTextKey, setSelectedTextKey] = useState<string>("");
  const [editableTexts, setEditableTexts] = useState<Record<string, string>>(
    {}
  );

  const handleInputChange = (
    field: keyof ReportConfig,
    value: string | boolean
  ) => {
    onConfigChange({
      ...reportConfig,
      [field]: value,
    });
  };

  const handleTextSelect = (key: string, text: string) => {
    setSelectedTextKey(key);
    if (!editableTexts[key]) {
      setEditableTexts((prev) => ({
        ...prev,
        [key]: text,
      }));
    }
  };

  const handleEditableTextChange = (key: string, value: string) => {
    if (key === "customTitle") {
      onConfigChange({
        ...reportConfig,
        customTitle: value,
      });
    } else {
      setEditableTexts((prev) => ({
        ...prev,
        [key]: value,
      }));

      onConfigChange({
        ...reportConfig,
        editableTexts: {
          ...reportConfig.editableTexts,
          [key]: value,
        },
      });
    }
  };

  return (
    <div className={styles.container}>
      {/* <div className={styles.editorPanel}>
        <div className={styles.formGroup}>
          <InputField
            title="보고서 제목"
            value={reportConfig.customTitle}
            onChange={(value) => handleInputChange("customTitle", value)}
            placeholder="리포트 제목을 입력하세요"
            showClearButton={true}
          />
        </div>

        {selectedTextKey && (
          <div className={styles.formGroup}>
            <InputField
              title={`선택된 텍스트 편집 (${selectedTextKey})`}
              value={editableTexts[selectedTextKey] || ""}
              onChange={(value) => handleEditableTextChange(selectedTextKey, value)}
              placeholder="텍스트를 수정하세요"
              multiline
              showClearButton={true}
            />
          </div>
        )}
      </div> */}

      <div className={styles.previewPanel}>
        <ReportViewer
          reportData={reportData}
          reportConfig={reportConfig}
          isEditing={true}
          selectedTextKey={selectedTextKey}
          editableTexts={editableTexts}
          onTextSelect={handleTextSelect}
          onEditText={handleEditableTextChange}
        />
      </div>
    </div>
  );
};

export default ReportEditor;
