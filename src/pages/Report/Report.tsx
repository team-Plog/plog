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
} from "../../components/ModeToggleDropdown/ModeToggleDropdown";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

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

  // 2) 캐스팅/좁히기
  const handleModeChange = (selected: DropdownOption) => {
    setIsEditing(Boolean((selected as {value: unknown}).value));
  };

  // Report.tsx의 generatePDF 함수를 이것으로 교체하세요

const generatePDF = async () => {
  if (!reportViewerRef.current || pdfGenerating) return;

  setPdfGenerating(true);
  try {
    const element = reportViewerRef.current;
    
    // 1. 캡처 전 요소 스타일 최적화
    const originalStyles = {
      maxHeight: element.style.maxHeight,
      overflow: element.style.overflow,
      height: element.style.height
    };
    
    // 캡처를 위한 임시 스타일 적용
    element.style.maxHeight = 'none';
    element.style.overflow = 'visible';
    element.style.height = 'auto';

    // 2. 더 정확한 캡처 설정
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: "#ffffff",
      logging: false,
      scrollX: 0,
      scrollY: 0,
      windowWidth: element.scrollWidth,
      windowHeight: element.scrollHeight,
      onclone: (clonedDoc) => {
        // 클론된 문서에서 PDF 캡처용 스타일 적용
        const clonedElement = clonedDoc.querySelector("[data-pdf-capture]") as HTMLElement;
        if (clonedElement) {
          clonedElement.style.maxHeight = "none";
          clonedElement.style.overflow = "visible";
          clonedElement.style.height = "auto";
          clonedElement.style.transform = "none";
        }
        
        // 스크롤 컨테이너 정리
        const scrollContainers = clonedDoc.querySelectorAll('.previewContainer');
        scrollContainers.forEach(container => {
          (container as HTMLElement).style.overflow = 'visible';
          (container as HTMLElement).style.maxHeight = 'none';
        });
      },
    });

    // 3. 원본 스타일 복원
    element.style.maxHeight = originalStyles.maxHeight;
    element.style.overflow = originalStyles.overflow;
    element.style.height = originalStyles.height;

    const imgData = canvas.toDataURL("image/png", 0.95); // 압축률 조정

    // 4. PDF 생성 with 정확한 페이지 분할
    const pdf = new jsPDF("p", "mm", "a4");
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    
    // 여백 설정
    const margin = 10;
    const contentWidth = pdfWidth - (margin * 2);
    const contentHeight = pdfHeight - (margin * 2);
    
    // 이미지 크기 계산
    const imgWidth = contentWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    // 페이지당 콘텐츠 높이
    const pageContentHeight = contentHeight;
    
    let yPosition = 0;
    let pageCount = 0;
    
    while (yPosition < imgHeight) {
      if (pageCount > 0) {
        pdf.addPage();
      }
      
      // 현재 페이지에 들어갈 이미지의 높이 계산
      const remainingHeight = imgHeight - yPosition;
      const currentPageHeight = Math.min(pageContentHeight, remainingHeight);
      
      // 소스 이미지에서 현재 페이지 부분의 시작 y 좌표 계산
      const sourceY = (yPosition / imgHeight) * canvas.height;
      const sourceHeight = (currentPageHeight / imgHeight) * canvas.height;
      
      // 캔버스에서 현재 페이지 부분만 추출
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = sourceHeight;
      
      const pageCtx = pageCanvas.getContext('2d');
      if (pageCtx) {
        pageCtx.drawImage(
          canvas, 
          0, sourceY, canvas.width, sourceHeight,  // 소스 영역
          0, 0, canvas.width, sourceHeight         // 대상 영역
        );
        
        const pageImgData = pageCanvas.toDataURL("image/png", 0.95);
        
        // PDF에 현재 페이지 이미지 추가
        pdf.addImage(
          pageImgData, 
          "PNG", 
          margin, 
          margin, 
          imgWidth, 
          currentPageHeight
        );
      }
      
      yPosition += pageContentHeight;
      pageCount++;
    }

    // 5. PDF 저장
    const fileName = `${reportConfig.customTitle || "성능테스트리포트"}_${
      new Date().toISOString().split("T")[0]
    }.pdf`;
    
    pdf.save(fileName);
    
  } catch (error) {
    console.error("PDF 생성 실패:", error);
    alert("PDF 생성 중 오류가 발생했습니다.");
  } finally {
    setPdfGenerating(false);
  }
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

                    <Button icon={<Printer />} onClick={() => window.print()}>
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