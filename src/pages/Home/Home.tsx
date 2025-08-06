import React, {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {Plus, Menu, History} from "lucide-react";
import {SearchBar} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import ProjectCard from "../../components/ProjectCard/ProjectCard";
import MainModal from "../../components/MainModal/MainModal";
import Header from "../../components/Header/Header";
import EmptyProjectState from "../../components/EmptyState/EmptyProjectState";
import styles from "./Home.module.css";
import {getProjectList, getTestHistoryList} from "../../api";
import {StatusBadge, type TestStatus} from "../../components/Tag";

interface Project {
  id: number;
  title: string;
  summary: string;
  status: string | null;
  updated_at: string | null;
}

interface TestHistoryItem {
  project_title: string;
  test_title: string;
  status_datetime: string;
  test_status: string;
}

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [testHistory, setTestHistory] = useState<TestHistoryItem[]>([]);

  const handleProjectClick = (projectId: number) => {
    navigate("/projectDetail", {state: {projectId}});
  };

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

  useEffect(() => {
    getProjectList()
      .then((res) => {
        console.log("📦 받아온 프로젝트 리스트:", res.data);
        setProjects(res.data.data);
      })
      .catch((err) => {
        console.error("❌ 프로젝트 리스트 가져오기 실패:", err);
      });
  }, []);

  useEffect(() => {
    getTestHistoryList(0, 5)
      .then((res) => {
        console.log("🕒 최근 실행 기록:", res.data);
        setTestHistory(res.data.data);
      })
      .catch((err) => {
        console.error("❌ 최근 실행 기록 가져오기 실패:", err);
      });
  }, []);

  // 검색 필터링 로직
  const hasProjects = projects.length > 0;
  const filteredProjects = projects.filter(
    (project) =>
      project.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      project.summary.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerInner}>
            {/* Left Group - Menu and Title */}
            <div className={styles.leftGroup}>
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className={styles.menuButton}>
                <Menu className={styles.menuIcon} />
              </button>
              <h1 className={`HeadingS ${styles.title}`}>내 프로젝트</h1>
            </div>
            {/* Right Group - Search Bar and Button */}
            <div className={styles.rightGroup}>
              <div className={styles.searchContainer}>
                <SearchBar
                  value={searchTerm}
                  onChange={setSearchTerm}
                  placeholder="검색어를 입력하세요"
                />
              </div>
              <Button
                variant="primaryGradient"
                onClick={() => setIsModalOpen(true)}
                icon={<Plus />}>
                새 프로젝트 추가하기
              </Button>
            </div>
          </div>
        </header>

        {isModalOpen && <MainModal onClose={() => setIsModalOpen(false)} />}

        {/* Main Content */}
        <main className={styles.main}>
          {hasProjects ? (
            /* Projects Grid */
            <div className={styles.projectsGrid}>
              {filteredProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  id={project.id}
                  title={project.title}
                  summary={project.summary}
                  status={(project.status ?? "before") as TestStatus}
                  updatedAt={project.updated_at}
                  onClick={handleProjectClick}
                />
              ))}
            </div>
          ) : (
            /* Empty State */
            <EmptyProjectState />
          )}
        </main>

        {/* 최근 실행 섹션 */}
        <div className={styles.recentRunning}>
          <div className={styles.leftGroup}>
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className={styles.menuButton}>
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
                  {item.project_title}
                </div>
                <div className={`Body ${styles.tableCell}`}>
                  {item.test_title}
                </div>
                <div className={`Body ${styles.tableCell}`}>
                  {new Date(item.status_datetime).toLocaleDateString("ko-KR", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false
                  })}
                </div>
              </div>
            ))
          ) : (
            <div className={styles.noHistory}>최근 실행 기록이 없습니다.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Home;
