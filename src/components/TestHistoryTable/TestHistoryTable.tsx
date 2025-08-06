import React from "react";
import { History } from "lucide-react";
import { StatusBadge, type TestStatus } from "../Tag";
import styles from "./TestHistoryTable.module.css";

interface TestHistoryItem {
  project_title: string;
  test_title: string;
  status_datetime: string;
  test_status: string;
}

interface TestHistoryTableProps {
  testHistory: TestHistoryItem[];
  onMenuToggle: () => void;
}

const TestHistoryTable: React.FC<TestHistoryTableProps> = ({
  testHistory,
  onMenuToggle,
}) => {
  // 테스트 상태를 StatusBadge에서 사용할 수 있는 형태로 변환
  const mapTestStatusToStatusBadge = (status: string): TestStatus => {
    switch (status) {
      case "실행 중":
        return "running";
      case "완료":
        return "completed";
      case "실패":
        return "failed";
      default:
        return "before";
    }
  };

  return (
    <div className={styles.recentRunning}>
      {/* 헤더 */}
      <div className={styles.leftGroup}>
        <button onClick={onMenuToggle} className={styles.menuButton}>
          <History className={styles.menuIcon} />
        </button>
        <h1 className={`HeadingS ${styles.title}`}>최근 실행</h1>
      </div>

      {/* 테이블 헤더 */}
      <div className={styles.tableHeader}>
        <div className={`Body ${styles.headerItem}`}>상태</div>
        <div className={`Body ${styles.headerItem}`}>테스트명</div>
        <div className={`Body ${styles.headerItem}`}>프로젝트명</div>
        <div className={`Body ${styles.headerItem}`}>마지막 테스트</div>
      </div>

      {/* 테이블 내용 */}
      {testHistory.length > 0 ? (
        testHistory.map((item, index) => (
          <div key={index} className={styles.tableRow}>
            <div className={styles.statusCell}>
              <StatusBadge
                status={mapTestStatusToStatusBadge(item.test_status)}
              />
            </div>
            <div className={`Body ${styles.tableCell}`}>
              {item.test_title}
            </div>
            <div className={`Body ${styles.tableCell}`}>
              {item.project_title}
            </div>
            <div className={`Body ${styles.tableCell}`}>
              {new Date(item.status_datetime).toLocaleDateString("ko-KR", {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
              })}
            </div>
          </div>
        ))
      ) : (
        <div className={styles.noHistory}>최근 실행 기록이 없습니다.</div>
      )}
    </div>
  );
};

export default TestHistoryTable;