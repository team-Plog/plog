import React, { useState } from "react";
import { Plus, Menu, CirclePlus } from "lucide-react";
import { SearchBar } from "../../components/Input";
import { Button } from "../../components/Button/Button";
import ProjectCard from "../../components/ProjectCard/ProjectCard";
import type { ProjectCardProps } from "../../components/ProjectCard/types";
import MainModal from "../../components/MainModal/MainModal";
import Header from "../../components/Header/Header";
import styles from "./Home.module.css";

const Home: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // 임시 프로젝트 데이터
  const mockProjects: ProjectCardProps[] = [
    {
      id: "1",
      title: "API 부하 테스트 프로젝트",
      description:
        "사용자 인증 API의 성능을 측정하고 병목 구간을 파악하기 위한 부하 테스트입니다.긴텍스트긴텍스트긴텍스트긴텍스트긴텍스트",
      status: "completed",
      createdAt: "2024-01-15T09:30:00Z",
    },
    {
      id: "2",
      title: "결제 시스템 성능 테스트",
      description: "결제 처리 시스템의 동시 접속자 처리 능력을 확인합니다.",
      status: "running",
      createdAt: "2024-01-20T14:15:00Z",
    },
    {
      id: "3",
      title: "데이터베이스 쿼리 최적화",
      description:
        "복잡한 조인 쿼리의 성능을 테스트하고 최적화 방안을 도출합니다.",
      status: "failed",
      createdAt: "2024-01-18T11:45:00Z",
    },
    {
      id: "4",
      title: "신규 기능 API 테스트",
      description: "새로 개발된 API 엔드포인트들의 부하 테스트를 진행합니다.",
      status: "before",
      createdAt: "2024-01-22T16:20:00Z",
    },
  ];

  const handleProjectClick = (projectId: string) => {
    console.log("Project clicked:", projectId);
  };

  // 프로젝트가 있는지 확인 (테스트를 위해 false로 설정하면 Empty State 확인 가능)
  const hasProjects = mockProjects.length > 0;
  const [isModalOpen, setIsModalOpen] = useState(false);

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
                className={styles.menuButton}
              >
                <Menu className={styles.menuIcon} />
              </button>
              <h1 className={`HeadingS ${styles.title}`}>
                내 프로젝트
              </h1>
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
              >
                <Plus className={styles.buttonIcon} />
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
              {mockProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  {...project}
                  onClick={handleProjectClick}
                />
              ))}
            </div>
          ) : (
            /* Empty State Container */
            <div className={styles.emptyState}>
              {/* Icon Container */}
              <div className={styles.emptyIconContainer}>
                <CirclePlus className={styles.emptyIcon} />
              </div>

              {/* Text Content */}
              <div className={styles.emptyTextContent}>
                <p className={`HeadingS ${styles.emptyTitle}`}>
                  아직 생성된 프로젝트가 없습니다.
                </p>
                <p className={`Body ${styles.emptyDescription}`}>
                  부하 테스트를 시작하려면 새로운 프로젝트를 생성하세요.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default Home;