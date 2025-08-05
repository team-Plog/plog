import React, {useEffect, useState} from "react";
import styles from "./Header.module.css";
import "../../assets/styles/typography.css";
import {ChevronLeft, ChevronRight, Moon} from "lucide-react";
import {useNavigate, useLocation} from "react-router-dom";
import {getProjectDetail} from "../../api";

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [projectTitle, setProjectTitle] = useState<string>("");

  const goBack = () => window.history.back();
  const goForward = () => window.history.forward();

  // 현재 경로가 프로젝트 상세 페이지인지 확인
  const isProjectPage = location.pathname === "/projectDetail";
  const projectId = location.state?.projectId;

  // 프로젝트 상세 페이지에서 프로젝트 제목 가져오기
  useEffect(() => {
    if (isProjectPage && projectId) {
      getProjectDetail(projectId)
        .then((res) => {
          setProjectTitle(res.data.data.title);
        })
        .catch((err) => {
          console.error("프로젝트 정보 가져오기 실패:", err);
          setProjectTitle("프로젝트");
        });
    } else {
      setProjectTitle("");
    }
  }, [isProjectPage, projectId]);

  const handleNavigateToMain = () => {
    navigate("/");
  };

  const handleNavigateToReport = () => {
    navigate("/report", {state: {projectId}});
  };

  return (
    <div className={styles.header}>
      <div className={styles.title}>
        <div className={styles.filledCircle} />
        <div className="HeadingS">PLog</div>
        <div className={styles.button}>
          <ChevronLeft onClick={goBack} />
          <ChevronRight onClick={goForward} />
        </div>
        {isProjectPage && projectId && (
          <div className={styles.navMenu}>
            <button
              className={`${styles.navButton} Body`}
              onClick={handleNavigateToMain}>
              메인
            </button>
            <div className={`${styles.navButton} Body`}>/</div>
            <button className={`${styles.navButton} Body`} onClick={() => {}}>
              {projectTitle || "프로젝트 타이틀"}
            </button>
            <div className={`${styles.navButton} Body`}>/</div>
            <button
              className={`${styles.navButton} Body`}
              onClick={handleNavigateToReport}>
              보고서
            </button>
          </div>
        )}
      </div>
      <div className={styles.moonIcon}>
        <Moon />
      </div>
    </div>
  );
};

export default Header;
