import React, {useState} from "react";
import styles from "./ReportEditor.module.css";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import ReportViewer from "./ReportViewer";

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
