import React, {useEffect, useState} from "react";
import styles from "./Header.module.css";
import "../../assets/styles/typography.css";
import {ChevronLeft, ChevronRight, Moon} from "lucide-react";
import {useNavigate, useLocation} from "react-router-dom";
import {getProjectDetail} from "../../api";

// Header.tsx
const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [projectTitle, setProjectTitle] = useState<string>("");

  const goBack = () => window.history.back();
  const goForward = () => window.history.forward();

  // 현재 경로 상태
  const isProjectPage = location.pathname === "/projectDetail";
  const isTestPage = location.pathname === "/test";
  const projectId = location.state?.projectId;
  const testTitle = location.state?.testTitle; // 시나리오명 받기

  // 프로젝트 제목 로딩
  useEffect(() => {
    if ((isProjectPage || isTestPage) && projectId) {
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
  }, [isProjectPage, isTestPage, projectId]);

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

        {/* 프로젝트 상세 페이지 or 테스트 페이지일 때 메뉴 표시 */}
        {(isProjectPage || isTestPage) && projectId && (
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

            {/* 테스트 페이지일 때 시나리오명 추가 */}
            {isTestPage && (
              <>
                <div className={`${styles.navButton} Body`}>/</div>
                <button
                  className={`${styles.navButton} Body`}
                  onClick={() => {}}>
                  {testTitle || "시나리오명"}
                </button>
              </>
            )}

            {/* 보고서 버튼은 프로젝트 상세 페이지에서만 */}
            {isProjectPage && (
              <>
                <div className={`${styles.navButton} Body`}>/</div>
                <button
                  className={`${styles.navButton} Body`}
                  onClick={handleNavigateToReport}>
                  보고서
                </button>
              </>
            )}
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
