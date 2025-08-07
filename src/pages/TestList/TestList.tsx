import React from "react";
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

  React.useEffect(() => {
    if (projectId) {
      getTestHistoryByProject(projectId)
        .then((res) => {
          setTestHistory(res.data.data); // API 응답에 맞게 수정
        })
        .catch((err) => {
          console.error("테스트 이력 불러오기 실패:", err);
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
