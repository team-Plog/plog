import React, {useState} from "react";
import {History, Trash2} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {StatusBadge, type TestStatus} from "../Tag";
import EmptyState from "../EmptyState/EmptyState";
import styles from "./TestHistoryTable.module.css";
import {deleteTestHistory} from "../../api";

interface TestHistoryItem {
  test_history_id: number;
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
  hideEmptyState?: boolean;
  onDeleteSuccess?: (id: number) => void;
}

const TestHistoryTable: React.FC<TestHistoryTableProps> = ({
  testHistory,
  onMenuToggle,
  titleText = "최근 실행",
  hideProjectTitleColumn = false,
  hideEmptyState = false,
  onDeleteSuccess,
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
      case "문서 생성 중":
        return "analyzing";
      case "문서 생성 완료":
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
        testHistoryId: item.test_history_id,
      },
    });
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!window.confirm("정말 삭제하시겠습니까?")) return;

    try {
      await deleteTestHistory(id);
      alert("삭제되었습니다.");
      window.location.reload();
    } catch (err) {
      console.error("삭제 실패:", err);
      alert("삭제에 실패했습니다.");
    }
  };

  return (
    <div className={styles.recentRunning}>
      {/* 테스트 이력이 없고 hideEmptyState가 true인 경우 아무것도 표시하지 않음 */}
      {testHistory.length === 0 &&
      hideEmptyState ? null : testHistory.length === 0 ? (
        <div className={styles.emptyStateContainer}>
          <EmptyState type="test" />
        </div>
      ) : (
        <>
          {/* 헤더 */}
          <div className={styles.leftGroup}>
            <History className={styles.menuIcon} />
            <h1 className={`HeadingS ${styles.title}`}>{titleText}</h1>
          </div>
          {/* 테이블 헤더 */}
          <div className={styles.tableHeader}>
            <div className={`Body ${styles.headerItem}`}>상태</div>
            <div className={`Body ${styles.headerItem}`}>테스트명</div>
            {!hideProjectTitleColumn && (
              <div className={`Body ${styles.headerItem}`}>프로젝트명</div>
            )}
            <div className={`Body ${styles.headerItem}`}>마지막 테스트</div>
            <div className={`Body ${styles.headerItem}`}>삭제</div>
            </div>

          {/* 테이블 내용 */}
          {paginatedData.map((item, index) => (
            <div
              key={index}
              className={`${styles.tableRow} ${styles.clickableRow}`}
              onClick={() => handleRowClick(item)}>
              <div className={styles.statusCell}>
                <StatusBadge
                  status={mapTestStatusToStatusBadge(item.test_status)}
                />
              </div>
              <div className={`Body ${styles.tableCell}`}>
                {item.test_title}
              </div>
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
              <div className={`Body ${styles.tableCell}`}>
                <button
                  className={styles.deleteButton}
                  onClick={(e) => handleDelete(e, item.test_history_id)}>
                  <Trash2 className={styles.icon} />
                </button>
              </div>
            </div>
          ))}

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              {Array.from({length: totalPages}, (_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`${styles.pageButton} ${
                    currentPage === i + 1 ? styles.active : ""
                  }`}>
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default TestHistoryTable;
