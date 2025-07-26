import React, {useState} from "react";
import {useNavigate} from "react-router-dom";
import {Plus, Menu} from "lucide-react";
import {SearchBar} from "../../components/Input";
import {Button} from "../../components/Button/Button";
import ProjectCard from "../../components/ProjectCard/ProjectCard";
import MainModal from "../../components/MainModal/MainModal";
import Header from "../../components/Header/Header";
import EmptyProjectState from "../../components/EmptyState/EmptyProjectState";
import {mockProjects} from "../../assets/mockProjectData";
import styles from "./Home.module.css";

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleProjectClick = (projectId: string) => {
    navigate("/projectDetail", { state: { projectId } });
  };

  // 프로젝트가 있는지 확인 (테스트를 위해 false로 설정하면 Empty State 확인 가능)
  const hasProjects = mockProjects.length > 0;
  const [isModalOpen, setIsModalOpen] = useState(false);

  // 검색 필터링 로직
  const filteredProjects = mockProjects.filter(project =>
    project.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    project.description.toLowerCase().includes(searchTerm.toLowerCase())
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
                  description={project.description}
                  status={project.status}
                  createdAt={project.createdAt}
                  onClick={handleProjectClick}
                />
              ))}
            </div>
          ) : (
            /* Empty State */
            <EmptyProjectState />
          )}
        </main>
      </div>
    </div>
  );
};

export default Home;