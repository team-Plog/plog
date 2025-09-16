import React, {useEffect} from "react";
import styles from "./TestList.module.css";
import "../../assets/styles/typography.css";
import Header from "../../components/Header/Header";
import {useLocation} from "react-router-dom";
import TestHistoryTable from "../../components/TestHistoryTable/TestHistoryTable";
import {getTestHistoryByProject} from "../../api";

const TestList: React.FC = () => {
  const location = useLocation();
  const {projectId, projectTitle} = location.state || {};
  const [testHistory, setTestHistory] = React.useState([]);

  useEffect(() => {
    if (projectId) {
      getTestHistoryByProject(projectId)
        .then((res) => {
          console.log("📦 테스트 이력 API 응답:", res.data); // ✅ 여기 추가
          setTestHistory(res.data.data);
        })
        .catch((err) => {
          console.error("❌ 테스트 이력 불러오기 실패:", err);
        });
    }
  }, [projectId]);

  const handleMenuToggle = () => {
    console.log("메뉴 클릭됨");
  };

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <TestHistoryTable
          testHistory={testHistory}
          onMenuToggle={handleMenuToggle}
          titleText={projectTitle}
          hideProjectTitleColumn={true}
        />
      </div>
    </div>
  );
};

export default TestList;
