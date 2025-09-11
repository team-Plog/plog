import React, {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {Plus, Menu} from "lucide-react";
import {SearchBar} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import ProjectCard from "../../components/ProjectCard/ProjectCard";
import MainModal from "../../components/MainModal/MainModal";
import Header from "../../components/Header/Header";
import EmptyState from "../../components/EmptyState/EmptyState";
import TestHistoryTable from "../../components/TestHistoryTable/TestHistoryTable";
import styles from "./Home.module.css";
import {getProjectList, getTestHistoryList} from "../../api";
import {type TestStatus} from "../../components/Tag";

interface Project {
  id: number;
  title: string;
  summary: string;
  status: string | null;
  updated_at: string | null;
}

interface TestHistoryItem {
  test_history_id: number;
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
    getTestHistoryList(0, 100)
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
            <EmptyState type="project" />
          )}
        </main>

        {/* 최근 실행 섹션 - hideEmptyState를 true로 설정 */}
        <TestHistoryTable
          testHistory={testHistory}
          onMenuToggle={() => setIsMenuOpen(!isMenuOpen)}
          hideEmptyState={true}
        />
      </div>
    </div>
  );
};

export default Home;