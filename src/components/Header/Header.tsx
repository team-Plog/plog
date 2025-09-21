import React, { useEffect, useState } from 'react';
import styles from './Header.module.css';
import '../../assets/styles/typography.css';
import { ChevronLeft, ChevronRight, List, Moon, Sun } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getProjectDetail } from '../../api';
import Logo from '../../assets/images/logo.svg?react';

interface HeaderProps {
  testHistoryId?: number | null;
}

const Header: React.FC<HeaderProps> = ({ testHistoryId }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [projectTitle, setProjectTitle] = useState<string>('');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);

  const goBack = () => window.history.back();
  const goForward = () => window.history.forward();

  // 다크 모드 토글 함수
  const toggleDarkMode = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);

    // localStorage에 테마 설정 저장
    localStorage.setItem('theme', newDarkMode ? 'dark' : 'light');

    // HTML root element에 data-theme 속성 설정
    if (newDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  };

  // 컴포넌트 마운트 시 저장된 테마 설정 불러오기
  useEffect(() => {
    // localStorage에서 저장된 테마 설정 확인
    const savedTheme = localStorage.getItem('theme');
    
    // 저장된 테마가 없으면 시스템 기본 설정 확인
    if (!savedTheme) {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const initialTheme = prefersDark ? 'dark' : 'light';
      localStorage.setItem('theme', initialTheme);
      
      if (initialTheme === 'dark') {
        setIsDarkMode(true);
        document.documentElement.setAttribute('data-theme', 'dark');
      }
    } else if (savedTheme === 'dark') {
      setIsDarkMode(true);
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  // 현재 경로 상태
  const isProjectPage = location.pathname === '/projectDetail';
  const isTestPage = location.pathname === '/test';
  const isReportPage = location.pathname === '/report';
  const projectId = location.state?.projectId;
  const testTitle = location.state?.testTitle;
  const stateTestHistoryId = location.state?.testHistoryId ?? null;
  const effectiveTestHistoryId = testHistoryId ?? stateTestHistoryId;

  // 프로젝트 제목 로딩
  useEffect(() => {
    if ((isProjectPage || isTestPage || isReportPage) && projectId) {
      getProjectDetail(projectId)
        .then((res) => {
          setProjectTitle(res.data.data.title);
        })
        .catch((err) => {
          console.error('프로젝트 정보 가져오기 실패:', err);
          setProjectTitle('프로젝트');
        });
    } else {
      setProjectTitle('');
    }
  }, [isProjectPage, isTestPage, isReportPage, projectId]);

  const handleNavigateToMain = () => {
    navigate('/');
  };

  const handleNavigateToProjectDetail = () => {
    if (!projectId) return;
    navigate('/projectDetail', { state: { projectId, projectTitle } });
  };

  const handleNavigateToTest = () => {
    if (!projectId || !testTitle) return;
    navigate('/test', {
      state: { projectId, testTitle, testHistoryId: effectiveTestHistoryId },
    });
  };

  const handleNavigateToReport = () => {
    navigate('/report', {
      state: { projectId, testHistoryId, testTitle, projectTitle },
    });
  };

  return (
    <div className={styles.header}>
      <div className={styles.title}>
        <div className={styles.logo} onClick={handleNavigateToMain}>
          <Logo className={styles.logoIcon} />
        </div>
        <div className={styles.button}>
          <ChevronLeft onClick={goBack} />
          <ChevronRight onClick={goForward} />
        </div>

        {/* 프로젝트 상세, 테스트, 리포트 페이지일 때 메뉴 표시 */}
        {(isProjectPage || isTestPage || isReportPage) && projectId && (
          <div className={styles.navMenu}>
            <button
              className={`${styles.navButton} Body`}
              onClick={handleNavigateToMain}
            >
              메인
            </button>
            <div className={`${styles.navButton} Body`}>/</div>
            <button
              className={`${styles.navButton} Body`}
              onClick={handleNavigateToProjectDetail}
            >
              {projectTitle || '프로젝트 타이틀'}
            </button>

            {/* 테스트 페이지 또는 리포트 페이지일 때 시나리오명 추가 */}
            {(isTestPage || isReportPage) && (
              <>
                <div className={`${styles.navButton} Body`}>/</div>
                <button
                  className={`${styles.navButton} Body`}
                  onClick={handleNavigateToTest}
                >
                  {testTitle || '시나리오명'}
                </button>
              </>
            )}

            {/* 리포트 페이지가 아닐 때만 '보고서' 버튼 표시 */}
            {(isProjectPage || isTestPage || isReportPage) &&
              effectiveTestHistoryId && (
                <>
                  <div className={`${styles.navButton} Body`}>/</div>
                  <button
                    className={`${styles.navButton} Body`}
                    onClick={handleNavigateToReport}
                  >
                    보고서
                  </button>
                </>
              )}
          </div>
        )}
      </div>
      <div className={styles.iconWrapper}>
        {isProjectPage && (
          <div
            className={styles.icon}
            onClick={() =>
              navigate('/testList', {
                state: {
                  projectId,
                  projectTitle,
                },
              })
            }
          >
            <List />
          </div>
        )}
        <div className={styles.icon} onClick={toggleDarkMode}>
          {isDarkMode ? <Sun /> : <Moon />}
        </div>
      </div>
    </div>
  );
};

export default Header;