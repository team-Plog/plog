import React, { useState } from "react";
import { History } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { StatusBadge, type TestStatus } from "../Tag";
import styles from "./TestHistoryTable.module.css";

interface TestHistoryItem {
  project_title: string;
  test_title: string;
  status_datetime: string;
  test_status: string;
  project_id?: number;
  job_name?: string;
}

interface TestHistoryTableProps {
  testHistory: TestHistoryItem[];
  onMenuToggle: () => void;
  titleText?: string;
  hideProjectTitleColumn?: boolean;
}

const TestHistoryTable: React.FC<TestHistoryTableProps> = ({
  testHistory,
  onMenuToggle,
  titleText = "최근 실행", 
  hideProjectTitleColumn = false, 
}) => {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const totalPages = Math.ceil(testHistory.length / itemsPerPage);
  const paginatedData = testHistory.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const mapTestStatusToStatusBadge = (status: string): TestStatus => {
    switch (status) {
      case "실행 중":
        return "running";
      case "테스트 완료":
        return "completed";
      case "실패":
        return "failed";
      default:
        return "before";
    }
  };

  const handleRowClick = (item: TestHistoryItem) => {
    navigate("/test", {
      state: {
        projectId: item.project_id,
        testTitle: item.test_title,
        jobName: item.job_name,
        projectTitle: item.project_title,
      },
    });
  };

  return (
    <div className={styles.recentRunning}>
      {/* 헤더 */}
      <div className={styles.leftGroup}>
        <button onClick={onMenuToggle} className={styles.menuButton}>
          <History className={styles.menuIcon} />
        </button>
        <h1 className={`HeadingS ${styles.title}`}>{titleText}</h1> {/* ✅ 적용 */}
      </div>

      {/* 테이블 헤더 */}
      <div className={styles.tableHeader}>
        <div className={`Body ${styles.headerItem}`}>상태</div>
        <div className={`Body ${styles.headerItem}`}>테스트명</div>
        {!hideProjectTitleColumn && (
          <div className={`Body ${styles.headerItem}`}>프로젝트명</div>
        )}
        <div className={`Body ${styles.headerItem}`}>마지막 테스트</div>
      </div>

      {/* 테이블 내용 */}
      {paginatedData.length > 0 ? (
        paginatedData.map((item, index) => (
          <div
            key={index}
            className={`${styles.tableRow} ${styles.clickableRow}`}
            onClick={() => handleRowClick(item)}
          >
            <div className={styles.statusCell}>
              <StatusBadge
                status={mapTestStatusToStatusBadge(item.test_status)}
              />
            </div>
            <div className={`Body ${styles.tableCell}`}>{item.test_title}</div>
            {!hideProjectTitleColumn && (
              <div className={`Body ${styles.tableCell}`}>
                {item.project_title}
              </div>
            )}
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

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              onClick={() => setCurrentPage(i + 1)}
              className={`${styles.pageButton} ${
                currentPage === i + 1 ? styles.active : ""
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default TestHistoryTable;
