import React, { useState } from "react";
import { Plus, Menu, PlusCircle } from "lucide-react";
import SearchBar from "../components/SearchBar/SearchBar";
import { Button } from "../components/Button/Button";
import ProjectCard from "../components/ProjectCard/ProjectCard";
import type { ProjectCardProps } from "../components/ProjectCard/types";
import MainModal from "../components/MainModal/MainModal";

const Home: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // 임시 프로젝트 데이터
  const mockProjects: ProjectCardProps[] = [
    {
      id: '1',
      title: 'API 부하 테스트 프로젝트',
      description: '사용자 인증 API의 성능을 측정하고 병목 구간을 파악하기 위한 부하 테스트입니다.',
      status: 'completed',
      createdAt: '2024-01-15T09:30:00Z'
    },
    {
      id: '2',
      title: '결제 시스템 성능 테스트',
      description: '결제 처리 시스템의 동시 접속자 처리 능력을 확인합니다.',
      status: 'running',
      createdAt: '2024-01-20T14:15:00Z'
    },
    {
      id: '3',
      title: '데이터베이스 쿼리 최적화',
      description: '복잡한 조인 쿼리의 성능을 테스트하고 최적화 방안을 도출합니다.',
      status: 'failed',
      createdAt: '2024-01-18T11:45:00Z'
    },
    {
      id: '4',
      title: '신규 기능 API 테스트',
      description: '새로 개발된 API 엔드포인트들의 부하 테스트를 진행합니다.',
      status: 'before',
      createdAt: '2024-01-22T16:20:00Z'
    }
  ];

  const handleProjectClick = (projectId: string) => {
    console.log("Project clicked:", projectId);
  };

  // 프로젝트가 있는지 확인 (테스트를 위해 false로 설정하면 Empty State 확인 가능)
  const hasProjects = mockProjects.length > 0;
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div
        style={{
          transition: "filter 0.2s",
          minHeight: "100vh",
          backgroundColor: "var(--color-background-secondary)",
          margin: 0,
          padding: 0,
          width: "100vw",
          boxSizing: "border-box",
        }}
      >
      {/* Header */}
      <header
        style={{
          padding: "var(--spacing-xl)",
          margin: 0,
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
            margin: 0,
            padding: 0,
          }}
        >
          {/* Left Group - Menu and Title */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--spacing-sm)",
            }}
          >
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              style={{
                padding: "var(--spacing-xs)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                transition: "background-color 0.2s",
              }}
            >
              <Menu
                style={{
                  width: "var(--icon-size-md)",
                  height: "var(--icon-size-md)",
                  color: "var(--color-gray-200)",
                }}
              />
            </button>
            <h1
              className="HeadingS"
              style={{
                color: "var(--color-black)",
                whiteSpace: 'nowrap',
                margin: 0,
              }}
            >
              내 프로젝트
            </h1>
          </div>

          {/* Right Group - Search Bar and Button */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "60px",
            }}
          >
            <div style={{ width: "300px" }}>
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
              <Plus style={{ width: "var(--icon-size-md)", height: "var(--icon-size-md)" }} />
              새 프로젝트 추가하기
            </Button>
          </div>
        </div>
      </header>

      {isModalOpen && <MainModal onClose={() => setIsModalOpen(false)} />}

      {/* Main Content */}
      <main
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "32px var(--spacing-lg)",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        {hasProjects ? (
          /* Projects Grid */
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "16px",
            }}
          >
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
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "400px",
              backgroundColor: "var(--color-gray-100)",
              border: "1px solid var(--color-border-primary)",
              borderRadius: "var(--radius-lg)",
              padding: "64px",
              gap: "64px",
            }}
          >
            {/* Icon Container */}
            <div
              style={{
                width: "200px",
                height: "160px",
                background: "linear-gradient(180deg, rgba(0, 0, 0, 0.07) 0%, rgba(0, 0, 0, 0.03) 100%)",
                border: "1px solid var(--color-border-primary)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 15px 0 rgba(0, 0, 0, 0.04) inset",
              }}
            >
              <PlusCircle
                style={{
                  width: "48px",
                  height: "48px",
                  color: "rgba(0, 0, 0, 0.1)",
                }}
              />
            </div>

            {/* Text Content */}
            <div
              style={{
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                gap: "var(--spacing-sm)",
              }}
            >
              <p
                className="HeadingS"
                style={{
                  color: "var(--color-black)",
                  margin: 0,
                }}
              >
                아직 생성된 프로젝트가 없습니다
              </p>
              <p
                className="Body"
                style={{
                  color: "var(--color-gray-300)",
                  margin: 0,
                }}
              >
                부하 테스트를 시작하려면 새로운 프로젝트를 생성하세요.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Home;
