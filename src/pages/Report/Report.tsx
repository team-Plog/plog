import React, {useEffect, useState, useRef} from "react";
import styles from "./Report.module.css";
import "../../assets/styles/typography.css";
import Header from "../../components/Header/Header";
import {Button} from "../../components/Button/Button";
import {useLocation} from "react-router-dom";
import {getTestHistoryDetail} from "../../api";
import ReportEditor from "../../components/Report/ReportEditor";
import ReportViewer from "../../components/Report/ReportViewer";
import EmptyState from "../../components/EmptyState/EmptyState";
import {Download, Printer, Eye, Pen} from "lucide-react";
import ModeToggleDropdown, {
  type DropdownOption,
} from "../../components/Dropdown/ModeToggleDropdown";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import html2pdf from "html2pdf.js";

export interface TestData {
  test_history_id: number;
  project_id: number;
  title: string;
  description: string;
  is_completed: boolean;
  completed_at: string;
  tested_at: string;
  job_name: string;
  k6_script_file_name: string;
  overall: {
    target_tps: number;
    total_requests: number;
    failed_requests: number;
    test_duration: number;
    tps: {
      max: number;
      min: number;
      avg: number;
    };
    response_time: {
      max: number;
      min: number;
      avg: number;
      p50: number;
      p95: number;
      p99: number;
    };
    error_rate: {
      max: number;
      min: number;
      avg: number;
    };
    vus: {
      max: number;
      min: number;
      avg: number;
    };
  };
  scenarios: Array<{
    scenario_history_id: number;
    name: string;
    scenario_tag: string;
    total_requests: number;
    failed_requests: number;
    test_duration: number;
    response_time_target: number;
    error_rate_target: number;
    think_time: number;
    executor: string;
    endpoint: {
      endpoint_id: number;
      method: string;
      path: string;
      description: string;
      summary: string;
    };
    tps: {
      max: number;
      min: number;
      avg: number;
    };
    response_time: {
      max: number;
      min: number;
      avg: number;
      p50: number;
      p95: number;
      p99: number;
    };
    error_rate: {
      max: number;
      min: number;
      avg: number;
    };
    stages: Array<{
      stage_history_id: number;
      duration: string;
      target: number;
    }>;
  }>;
}

export interface ReportConfig {
  includeExecutiveSummary: boolean;
  includeDetailedMetrics: boolean;
  includeScenarioBreakdown: boolean;
  includeCharts: boolean;
  customTitle: string;
  customDescription: string;
  editableTexts?: Record<string, string>;
  companyName?: string;
  reporterName?: string;
}

const Report: React.FC = () => {
  const location = useLocation();
  const {testHistoryId, projectId} = location.state || {};
  const [reportData, setReportData] = useState<TestData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [pdfGenerating, setPdfGenerating] = useState<boolean>(false);
  const reportViewerRef = useRef<HTMLDivElement>(null);

  const [reportConfig, setReportConfig] = useState<ReportConfig>({
    includeExecutiveSummary: true,
    includeDetailedMetrics: true,
    includeScenarioBreakdown: true,
    includeCharts: true,
    customTitle: "",
    customDescription: "",
  });

  // 드롭다운 옵션 정의
  const modeOptions: DropdownOption[] = [
    {
      id: "preview",
      label: "미리보기",
      icon: <Eye />,
      value: false,
    },
    {
      id: "edit",
      label: "편집 모드",
      icon: <Pen />,
      value: true,
    },
  ];

  const currentModeOption =
    modeOptions.find((option) => option.value === isEditing) || modeOptions[0];

  useEffect(() => {
    if (!testHistoryId) {
      setError("testHistoryId가 전달되지 않았습니다.");
      setLoading(false);
      return;
    }

    const fetchReportData = async () => {
      try {
        const res = await getTestHistoryDetail(testHistoryId);
        const data = res.data.data; // API 응답에서 실제 데이터 추출
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

  const handlePrint = () => {
    window.print();
  };

  // 2) 캐스팅/좁히기
  const handleModeChange = (selected: DropdownOption) => {
    setIsEditing(Boolean((selected as {value: unknown}).value));
  };

  const generatePDF = () => {
    if (!reportViewerRef.current) return;

    setPdfGenerating(true);

    const element = reportViewerRef.current;
    const opt = {
      margin: [0, 0, 0, 0] as [number, number, number, number],
      filename: `성능테스트리포트_${
        new Date().toISOString().split("T")[0]
      }.pdf`,
      image: {type: "jpeg", quality: 0.98},
      html2canvas: {scale: 2, useCORS: true},
      jsPDF: {unit: "mm", format: "a4", orientation: "portrait"},
      pagebreak: {
        mode: ["avoid-all", "css", "legacy"],
        before: ".documentHeader, .section",
      },
    };

    html2pdf()
      .set(opt)
      .from(element)
      .save()
      .finally(() => {
        setPdfGenerating(false);
      });
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

  // 테스트가 완료되지 않았을 때 EmptyState 표시
  if (!reportData.is_completed) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <div className={styles.emptyStateContainer}>
            <EmptyState type="report" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <div className={styles.reportContainer}>
          <div className={styles.headerAndContentContainer}>
            <div className={styles.header}>
              <div className={styles.headerLeft}>
                <ModeToggleDropdown
                  currentOption={currentModeOption}
                  options={modeOptions}
                  onSelect={handleModeChange}
                />
              </div>
              <div className={styles.headerRight}>
                {/* 미리보기 상태일 때만 저장/인쇄 버튼 표시 */}
                {!isEditing && (
                  <>
                    <Button
                      icon={<Download />}
                      onClick={generatePDF}
                      disabled={pdfGenerating}>
                      {pdfGenerating ? "PDF 생성 중..." : "저장하기"}
                    </Button>

                    <Button icon={<Printer />} onClick={handlePrint}>
                      인쇄하기
                    </Button>
                  </>
                )}
              </div>
            </div>

            <div className={styles.contentContainer}>
              {isEditing ? (
                <ReportEditor
                  reportData={reportData}
                  reportConfig={reportConfig}
                  onConfigChange={handleConfigChange}
                />
              ) : (
                <div ref={reportViewerRef} data-pdf-capture>
                  <ReportViewer
                    reportData={reportData}
                    reportConfig={reportConfig}
                    isEditing={false}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Report;
