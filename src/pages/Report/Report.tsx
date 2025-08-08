import React, {useEffect, useState} from "react";
import styles from "./Report.module.css";
import "../../assets/styles/typography.css";
import Header from "../../components/Header/Header";
import {Button} from "../../components/Button/Button";
import {useLocation} from "react-router-dom";
import {getTestHistoryDetail} from "../../api";
import ReportEditor from "../../components/Report/ReportEditor";
import ReportViewer from "../../components/Report/ReportViewer";
import {ChevronDown, Download, Eye, Pen, Pencil, Printer} from "lucide-react";
import {PDFDownloadLink} from "@react-pdf/renderer";
import PDFDocument from "../../components/Report/PDFDocument";

export interface TestData {
  target_tps: number | null;
  is_completed: boolean;
  error_rate: number;
  description: string;
  completed_at: string;
  total_requests: number;
  id: number;
  project_id: number;
  failed_requests: number;
  actual_tps: number;
  max_vus: number;
  title: string;
  avg_response_time: number;
  test_duration: number;
  tested_at: string;
  max_response_time: number;
  job_name: string;
  min_response_time: number;
  k6_script_file_name: string;
  p95_response_time: number;
  scenarios: Array<{
    name: string;
    scenario_name: string;
    failed_requests: number;
    id: number;
    actual_tps: number;
    test_history_id: number;
    endpoint_id: number;
    avg_response_time: number;
    executor: string;
    max_response_time: number;
    think_time: number;
    min_response_time: number;
    response_time_target: number | null;
    p95_response_time: number;
    error_rate_target: number | null;
    error_rate: number;
    total_requests: number;
    stages: Array<{
      id: number;
      scenario_id: number;
      duration: string;
      target: number;
    }>;
    endpoint: {
      method: string;
      path: string;
      description: string;
      id: number;
      summary: string;
    };
  }>;
}

export interface ReportConfig {
  includeExecutiveSummary: boolean;
  includeDetailedMetrics: boolean;
  includeScenarioBreakdown: boolean;
  includeCharts: boolean;
  customTitle: string;
  customDescription: string;
  companyName: string;
  reporterName: string;
}

const Report: React.FC = () => {
  const location = useLocation();
  const {testHistoryId, projectId} = location.state || {};
  const [reportData, setReportData] = useState<TestData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [reportConfig, setReportConfig] = useState<ReportConfig>({
    includeExecutiveSummary: true,
    includeDetailedMetrics: true,
    includeScenarioBreakdown: true,
    includeCharts: true,
    customTitle: "",
    customDescription: "",
    companyName: "",
    reporterName: "",
  });

  useEffect(() => {
    if (!testHistoryId) {
      setError("testHistoryId가 전달되지 않았습니다.");
      setLoading(false);
      return;
    }

    const fetchReportData = async () => {
      try {
        const res = await getTestHistoryDetail(testHistoryId);
        const data = res.data.data;
        setReportData(data);
        setReportConfig((prev) => ({
          ...prev,
          customTitle: data.title || "성능 테스트 리포트",
          customDescription: data.description || "설명 없음",
        }));
        console.log("✅ 테스트 리포트 데이터:", data);
      } catch (err) {
        console.error("❌ 테스트 리포트 정보 조회 실패:", err);
        setError("리포트 정보를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [testHistoryId]);

  const handleConfigChange = (newConfig: ReportConfig) => {
    setReportConfig(newConfig);
  };

  const toggleEditMode = () => {
    setIsEditing(!isEditing);
    setDropdownOpen(false);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <Header />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}></div>
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className={styles.container}>
        <Header />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <div className={styles.header}>
          {/* --- 헤더 왼쪽 영역 --- */}
          <div className={styles.headerLeft}>
            <div className={styles.modeToggle}>
              <div
                className={styles.customToggleButton}
                onClick={() => setDropdownOpen((prev) => !prev)}>
                <div className={styles.icon}>
                  {isEditing ? <Pen /> : <Eye />}
                </div>
                <span className="HeadingS">
                  {isEditing ? "편집 모드" : "미리보기"}
                </span>
                <div className={styles.icon}>
                  <ChevronDown />
                </div>
              </div>
              {dropdownOpen && (
                <div className={styles.dropdown}>
                  <div className={styles.icon}>
                    {isEditing ? <Eye /> : <Pen />}
                  </div>
                  <button className="HeadingS" onClick={toggleEditMode}>
                    {isEditing ? "미리보기" : "편집 모드"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* --- 헤더 오른쪽 영역 --- */}
          <div className={styles.headerRight}>
            {/* 미리보기 상태일 때만 저장/인쇄 버튼 표시 */}
            {!isEditing && (
              <>
                <PDFDownloadLink
                  document={
                    <PDFDocument
                      reportData={reportData}
                      reportConfig={reportConfig}
                    />
                  }
                  fileName={`${
                    reportConfig.customTitle || "성능테스트리포트"
                  }_${new Date().toISOString().split("T")[0]}.pdf`}>
                  {({loading}) => (
                    <Button icon={<Download />}>
                      {loading ? "PDF 생성 중..." : "저장하기"}
                    </Button>
                  )}
                </PDFDownloadLink>

                <Button icon={<Printer />} onClick={() => window.print()}>
                  인쇄하기
                </Button>
              </>
            )}
          </div>
        </div>

        {isEditing ? (
          <ReportEditor
            reportData={reportData}
            reportConfig={reportConfig}
            onConfigChange={handleConfigChange}
          />
        ) : (
          <ReportViewer
            reportData={reportData}
            reportConfig={reportConfig}
            isPreview={!isEditing}
          />
        )}
      </div>
    </div>
  );
};

export default Report;
