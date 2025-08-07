import React, {useEffect, useState} from "react";
import styles from "./Report.module.css";
import "../../assets/styles/typography.css";
import Header from "../../components/Header/Header";
import {Button} from "../../components/Button/Button";
import {useLocation} from "react-router-dom";
import {getTestHistoryDetail} from "../../api";
import ReportEditor from "../../components/Report/ReportEditor";
import ReportViewer from "../../components/Report/ReportViewer";

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
  const [reportConfig, setReportConfig] = useState<ReportConfig>({
    includeExecutiveSummary: true,
    includeDetailedMetrics: true,
    includeScenarioBreakdown: true,
    includeCharts: true,
    customTitle: "",
    customDescription: "",
    companyName: "",
    reporterName: ""
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
        setReportConfig(prev => ({
          ...prev,
          customTitle: data.title || "성능 테스트 리포트",
          customDescription: data.description || "설명 없음"
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
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <h1 className="HeadingS">📄 테스트 리포트</h1>
          <p className="Body">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <h1 className="HeadingS">📄 테스트 리포트</h1>
          <p className="Body" style={{color: "red"}}>
            {error}
          </p>
        </div>
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <h1 className="HeadingS">📄 테스트 리포트</h1>
          <p className="Body">리포트 데이터를 찾을 수 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <div className={styles.header}>
          <Button 
            variant="primaryGradient"
            onClick={toggleEditMode}
          >
            {isEditing ? "미리보기 모드로 전환" : "편집 모드로 전환"}
          </Button>
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
          />
        )}
      </div>
    </div>
  );
};

export default Report;