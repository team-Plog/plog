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

  const generatePDF = async () => {
    if (!reportViewerRef.current || pdfGenerating) return;

    setPdfGenerating(true);
    try {
      const element = reportViewerRef.current;

      // 1. 캡처 전 최적화
      const originalStyles = {
        maxHeight: element.style.maxHeight,
        overflow: element.style.overflow,
        height: element.style.height,
        position: element.style.position,
      };

      element.style.maxHeight = "none";
      element.style.overflow = "visible";
      element.style.height = "auto";
      element.style.position = "static";

      // 2. 모든 보호 대상 요소들 식별
      const protectedSelectors = [
        ".section", // 섹션 전체
        ".tableContainer", // 표 컨테이너
        ".summaryBox", // 요약 박스
        ".subTitleGroup", // 서브타이틀 그룹
        ".contentGroup", // 콘텐츠 그룹
        ".textGroup", // 텍스트 그룹
        "h1, h2, h3, h4, h5, h6", // 모든 제목
        "p", // 문단
        "table", // 표 자체
        ".documentHeader", // 문서 헤더
      ];

      const protectedElements: Array<{
        top: number;
        height: number;
        type: string;
        element: Element;
        priority: number;
      }> = [];

      // 각 선택자별로 요소 수집 및 우선순위 설정
      protectedSelectors.forEach((selector, index) => {
        const elements = element.querySelectorAll(selector);
        elements.forEach((el) => {
          const rect = el.getBoundingClientRect();
          const containerRect = element.getBoundingClientRect();

          // 우선순위 설정 (낮을수록 높은 우선순위)
          let priority = index;
          if (selector.includes("table")) priority = 0; // 표가 최우선
          else if (selector.includes("summaryBox")) priority = 1; // 요약박스
          else if (selector.includes("section")) priority = 2; // 섹션
          else if (selector.includes("Group")) priority = 3; // 그룹들
          else if (selector.includes("h1,h2,h3")) priority = 4; // 제목들

          protectedElements.push({
            top: rect.top - containerRect.top,
            height: rect.height,
            type: selector.replace(".", ""),
            element: el,
            priority: priority,
          });
        });
      });

      // 위치순 정렬 후 중복 제거 (부모-자식 관계 요소 중 우선순위 높은 것만 유지)
      protectedElements.sort((a, b) => a.top - b.top);

      // 중복되는 영역의 요소들 중 우선순위가 높은 것만 유지
      const uniqueElements = protectedElements.filter((current, index) => {
        return !protectedElements.some((other, otherIndex) => {
          if (index === otherIndex) return false;

          // 다른 요소 안에 완전히 포함되는지 확인
          const isContained =
            current.top >= other.top &&
            current.top + current.height <= other.top + other.height;

          // 포함되면서 우선순위가 낮으면 제거
          return isContained && current.priority > other.priority;
        });
      });

      // 3. 고해상도 전체 캡처
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: "#ffffff",
        logging: false,
        scrollX: 0,
        scrollY: 0,
        width: element.scrollWidth,
        height: element.scrollHeight,
        onclone: (clonedDoc) => {
          const clonedElement = clonedDoc.querySelector(
            "[data-pdf-capture]"
          ) as HTMLElement;
          if (clonedElement) {
            clonedElement.style.maxHeight = "none";
            clonedElement.style.overflow = "visible";
            clonedElement.style.height = "auto";
            clonedElement.style.position = "static";
          }
        },
      });

      // 4. 원본 스타일 복원
      Object.assign(element.style, originalStyles);

      // 5. PDF 설정
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      const margin = 15; // 15mm 여백
      const contentWidth = pdfWidth - margin * 2;
      const contentHeight = pdfHeight - margin * 2;

      // 6. 스마트 페이지 분할
      let canvasCurrentY = 0;
      let pageNumber = 0;

      // 캔버스 픽셀을 PDF mm로 변환하는 비율
      const pxToMm = 0.264583;
      const canvasWidthMm = canvas.width * pxToMm;
      const scale = contentWidth / canvasWidthMm;

      while (canvasCurrentY < canvas.height) {
        if (pageNumber > 0) {
          pdf.addPage();
        }

        // 이번 페이지에 들어갈 수 있는 최대 캔버스 높이 계산
        const maxCanvasHeightForPage = contentHeight / (pxToMm * scale);
        let nextCanvasY = Math.min(
          canvasCurrentY + maxCanvasHeightForPage,
          canvas.height
        );

        // 보호 대상 요소들이 잘리는지 확인
        for (const protectedEl of uniqueElements) {
          const elementTop = protectedEl.top;
          const elementBottom = protectedEl.top + protectedEl.height;

          // 요소가 페이지 경계에서 잘리는 경우
          if (elementTop < nextCanvasY && elementBottom > nextCanvasY) {
            const elementHeight = protectedEl.height;
            const availableSpace = nextCanvasY - canvasCurrentY;
            const requiredSpace = elementBottom - canvasCurrentY;

            // 요소 전체가 현재 페이지에 들어갈 수 있는지 확인
            if (
              requiredSpace <= maxCanvasHeightForPage &&
              elementTop >= canvasCurrentY
            ) {
              // 들어갈 수 있으면 현재 페이지에 포함
              nextCanvasY = elementBottom;
            } else {
              // 안 들어가면 다음 페이지로 미룸 (단, 현재 페이지에 충분한 내용이 있을 때만)
              const currentPageUsage =
                (elementTop - canvasCurrentY) / maxCanvasHeightForPage;

              if (currentPageUsage > 0.3) {
                // 현재 페이지를 30% 이상 사용했다면
                nextCanvasY = elementTop;
                break;
              } else {
                // 페이지 시작 부분이면 강제로 포함 (너무 큰 요소 처리)
                const maxAllowedHeight = maxCanvasHeightForPage * 0.9; // 페이지의 90%까지 허용
                if (elementHeight > maxAllowedHeight) {
                  // 너무 큰 요소는 여러 페이지에 걸쳐 분할
                  nextCanvasY = canvasCurrentY + maxCanvasHeightForPage;
                } else {
                  nextCanvasY = elementBottom;
                }
              }
            }
          }
        }

        // 실제 페이지에 포함될 높이
        const actualCanvasHeight = nextCanvasY - canvasCurrentY;

        // 최소 페이지 높이 보장 (너무 작은 조각 방지)
        if (
          actualCanvasHeight < maxCanvasHeightForPage * 0.1 &&
          canvasCurrentY + maxCanvasHeightForPage < canvas.height
        ) {
          nextCanvasY = canvasCurrentY + maxCanvasHeightForPage;
        }

        const finalCanvasHeight = nextCanvasY - canvasCurrentY;

        // 7. 페이지 캔버스 생성 및 이미지 추출
        const pageCanvas = document.createElement("canvas");
        pageCanvas.width = canvas.width;
        pageCanvas.height = finalCanvasHeight;

        const pageCtx = pageCanvas.getContext("2d");
        if (pageCtx) {
          // 흰색 배경
          pageCtx.fillStyle = "#ffffff";
          pageCtx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

          // 이미지 복사
          pageCtx.drawImage(
            canvas,
            0,
            canvasCurrentY,
            canvas.width,
            finalCanvasHeight,
            0,
            0,
            canvas.width,
            finalCanvasHeight
          );

          const pageImgData = pageCanvas.toDataURL("image/png", 1.0);

          // 8. PDF에 중앙 정렬로 추가
          const imgWidthMm = contentWidth;
          const imgHeightMm = finalCanvasHeight * pxToMm * scale;

          const xPosition = margin;
          const yPosition = margin;

          pdf.addImage(
            pageImgData,
            "PNG",
            xPosition,
            yPosition,
            imgWidthMm,
            Math.min(imgHeightMm, contentHeight)
          );
        }

        canvasCurrentY = nextCanvasY;
        pageNumber++;

        // 안전장치
        if (pageNumber > 50) {
          console.warn("페이지 수 제한 도달");
          break;
        }
      }

      // 9. 파일명 생성 및 저장
      const timestamp = new Date().toISOString().split("T")[0];
      const fileName = `${
        reportConfig.customTitle || "성능테스트리포트"
      }_${timestamp}.pdf`;
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
