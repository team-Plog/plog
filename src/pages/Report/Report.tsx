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

      // 1. CSS 변수에서 실제 배경색 값 가져오기
      const computedStyle = getComputedStyle(element);
      const whiteColor = computedStyle.getPropertyValue('--color-white').trim();
      const backgroundColor = whiteColor || '#ffffff';
      
      console.log('CSS 변수 --color-white 값:', backgroundColor);

      // 2. 캡처 전 최적화
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

      // 3. 보호 대상 요소들 식별 (모든 요소 보호)
      const protectedSelectors = [
        ".documentHeader", // 문서 헤더
        ".section", // 섹션 전체
        ".tableContainer", // 표 컨테이너
        ".table", // 표 자체
        "table", // 일반 표 태그
        "tr", // 테이블 행
        "tbody", // 테이블 본문
        "thead", // 테이블 헤더
        "tfoot", // 테이블 푸터
        ".summaryBox", // 요약 박스
        ".subTitleGroup", // 서브타이틀 그룹
        ".contentGroup", // 콘텐츠 그룹
        ".textGroup", // 텍스트 그룹
        
        // 차트 관련 선택자 강화
        "[class*='chart']", // 차트 관련 클래스 (기존)
        ".chart", // MetricChart의 메인 컨테이너
        ".recharts-wrapper", // Recharts 래퍼
        ".recharts-surface", // Recharts SVG 표면
        ".recharts-responsive-container", // Recharts 반응형 컨테이너
        "canvas", // 캔버스 요소
        "svg", // SVG 요소
        
        "h1, h2, h3, h4, h5, h6", // 모든 제목
        "p", // 문단
        ".HeadingL, .HeadingS, .TitleS", // 타이포그래피 클래스
        ".Body", // Body 클래스
      ];

      const protectedElements: Array<{
        top: number;
        height: number;
        bottom: number;
        type: string;
        element: Element;
      }> = [];

      // 모든 보호 대상 요소 수집 (우선순위 없음)
      protectedSelectors.forEach((selector) => {
        const elements = element.querySelectorAll(selector);
        elements.forEach((el) => {
          const rect = el.getBoundingClientRect();
          const containerRect = element.getBoundingClientRect();
          const top = rect.top - containerRect.top;
          const height = rect.height;

          protectedElements.push({
            top: top,
            height: height,
            bottom: top + height,
            type: selector.replace(".", ""),
            element: el,
          });
        });
      });

      // 위치순으로만 정렬 (중복 제거 안 함 - 모든 요소 보호)
      protectedElements.sort((a, b) => a.top - b.top);

      console.log(`총 ${protectedElements.length}개 요소가 보호 대상으로 설정됨:`, 
        protectedElements.map(el => ({ 
          type: el.type, 
          top: Math.round(el.top), 
          height: Math.round(el.height) 
        })));

      // 4. 고해상도 전체 캡처
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: backgroundColor,
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

      // 5. 원본 스타일 복원
      Object.assign(element.style, originalStyles);

      // 6. PDF 설정
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      const margin = 8;
      const contentWidth = pdfWidth - margin * 2;
      const contentHeight = pdfHeight - margin * 2;

      // 7. 스마트 페이지 분할 (모든 보호 요소 고려)
      let canvasCurrentY = 0;
      let pageNumber = 0;

      const pxToMm = 0.264583;
      const canvasWidthMm = canvas.width * pxToMm;
      const scale = contentWidth / canvasWidthMm;

      while (canvasCurrentY < canvas.height) {
        if (pageNumber > 0) {
          pdf.addPage();
        }

        const maxCanvasHeightForPage = contentHeight / (pxToMm * scale);
        let nextCanvasY = Math.min(
          canvasCurrentY + maxCanvasHeightForPage,
          canvas.height
        );

        console.log(`페이지 ${pageNumber + 1} 시작: Y=${Math.round(canvasCurrentY)}, 최대높이=${Math.round(maxCanvasHeightForPage)}`);

        // 모든 보호 대상 요소들이 잘리는지 확인
        let foundSplitElement = false;
        
        for (const protectedEl of protectedElements) {
          // 이 요소가 현재 페이지 범위에 있는지 확인
          if (protectedEl.top < nextCanvasY && protectedEl.bottom > nextCanvasY) {
            console.log(`요소 ${protectedEl.type} (${Math.round(protectedEl.top)}-${Math.round(protectedEl.bottom)})가 페이지 경계 ${Math.round(nextCanvasY)}에서 잘림`);
            
            const elementFitsInCurrentPage = 
              protectedEl.bottom - canvasCurrentY <= maxCanvasHeightForPage;
            const elementStartsInCurrentPage = protectedEl.top >= canvasCurrentY;
            
            if (elementFitsInCurrentPage && elementStartsInCurrentPage) {
              // 요소가 현재 페이지에 완전히 들어갈 수 있음
              nextCanvasY = protectedEl.bottom;
              console.log(`→ 요소를 현재 페이지에 완전 포함: ${Math.round(nextCanvasY)}`);
            } else {
              // 요소가 너무 크거나 이미 페이지 중간에서 시작
              const currentPageUsage = (protectedEl.top - canvasCurrentY) / maxCanvasHeightForPage;
              
              if (currentPageUsage > 0.2) { // 20% 이상 사용했다면 다음 페이지로
                nextCanvasY = protectedEl.top;
                console.log(`→ 다음 페이지로 미루기 (현재 사용률: ${(currentPageUsage * 100).toFixed(1)}%): ${Math.round(nextCanvasY)}`);
                foundSplitElement = true;
                break;
              } else if (protectedEl.height > maxCanvasHeightForPage * 0.8) {
                // 너무 큰 요소는 어쩔 수 없이 분할
                console.log(`→ 큰 요소 분할 허용 (높이: ${Math.round(protectedEl.height)})`);
                nextCanvasY = canvasCurrentY + maxCanvasHeightForPage;
              } else {
                // 작은 요소는 현재 페이지에 강제 포함
                nextCanvasY = protectedEl.bottom;
                console.log(`→ 작은 요소 강제 포함: ${Math.round(nextCanvasY)}`);
              }
            }
            
            break; // 첫 번째 충돌 요소만 처리
          }
        }

        // 최소 페이지 사용률 보장
        const actualCanvasHeight = nextCanvasY - canvasCurrentY;
        if (
          actualCanvasHeight < maxCanvasHeightForPage * 0.25 &&
          canvasCurrentY + maxCanvasHeightForPage < canvas.height &&
          !foundSplitElement
        ) {
          nextCanvasY = canvasCurrentY + maxCanvasHeightForPage;
          console.log(`최소 사용률 보장으로 조정: ${Math.round(nextCanvasY)}`);
        }

        const finalCanvasHeight = nextCanvasY - canvasCurrentY;
        console.log(`페이지 ${pageNumber + 1} 완료: ${Math.round(canvasCurrentY)} → ${Math.round(nextCanvasY)} (높이: ${Math.round(finalCanvasHeight)})`);

        // 8. 페이지 캔버스 생성
        const pageCanvas = document.createElement("canvas");
        pageCanvas.width = canvas.width;
        pageCanvas.height = finalCanvasHeight;

        const pageCtx = pageCanvas.getContext("2d");
        if (pageCtx) {
          // 배경색 채우기
          pageCtx.fillStyle = backgroundColor;
          pageCtx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

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

          // 9. PDF에 배경색 적용 후 이미지 추가
          if (backgroundColor.startsWith('#')) {
            pdf.setFillColor(backgroundColor);
          } else if (backgroundColor.startsWith('rgb')) {
            const rgbMatch = backgroundColor.match(/\d+/g);
            if (rgbMatch && rgbMatch.length >= 3) {
              pdf.setFillColor(parseInt(rgbMatch[0]), parseInt(rgbMatch[1]), parseInt(rgbMatch[2]));
            }
          }
          pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');

          const imgWidthMm = contentWidth;
          const imgHeightMm = finalCanvasHeight * pxToMm * scale;

          pdf.addImage(
            pageImgData,
            "PNG",
            margin,
            margin,
            imgWidthMm,
            Math.min(imgHeightMm, contentHeight)
          );
        }

        canvasCurrentY = nextCanvasY;
        pageNumber++;

        if (pageNumber > 50) {
          console.warn("페이지 수 제한 도달");
          break;
        }
      }

      console.log(`총 ${pageNumber}페이지 PDF 생성 완료`);

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