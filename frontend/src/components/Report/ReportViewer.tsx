import React, {useEffect, useState} from "react";
import styles from "./ReportViewer.module.css";
import {Sparkle} from "lucide-react";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import MetricChart from "../MetricChart/MetricChart";
import {
  getTestHistoryTimeseries,
  getTestHistoryResourceSummary,
  getAnalysisHistory,
} from "../../api";
import {InputField} from "../Input";
import Logo from "../../assets/images/logo.svg?react";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  isEditing?: boolean;
  selectedTextKey?: string;
  editableTexts?: Record<string, string>;
  onTextSelect?: (key: string, text: string) => void;
  onEditText?: (key: string, value: string) => void;
}

interface TimeseriesData {
  overall: {
    data: Array<{
      timestamp: string;
      tps: number;
      error_rate: number;
      vus: number;
      avg_response_time: number;
      p95_response_time: number;
      p99_response_time: number;
      [key: string]: any; // 동적 필드 지원
    }>;
  };
  scenarios: Array<{
    scenario_name: string;
    endpoint_summary: string;
    data: Array<{
      timestamp: string;
      tps: number;
      error_rate: number;
      vus: number;
      avg_response_time: number;
      p95_response_time: number;
      p99_response_time: number;
      [key: string]: any; // 동적 필드 지원
    }>;
  }>;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  reportData,
  reportConfig,
  isEditing = false,
  selectedTextKey,
  editableTexts,
  onTextSelect,
  onEditText,
}) => {
  const [timeseriesData, setTimeseriesData] = useState<TimeseriesData | null>(
    null
  );
  const [timeseriesLoading, setTimeseriesLoading] = useState<boolean>(false);
  const [resourceData, setResourceData] = useState<any[] | null>(null);
  const [resourceLoading, setResourceLoading] = useState<boolean>(false);
  const [analysisData, setAnalysisData] = useState<any[] | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);

  // 시계열 데이터 가져오기
  useEffect(() => {
    const fetchTimeseriesData = async () => {
      if (!reportData.test_history_id) return;

      setTimeseriesLoading(true);
      try {
        const res = await getTestHistoryTimeseries(reportData.test_history_id);
        setTimeseriesData(res.data.data);
      } catch (error) {
        console.error("시계열 데이터 조회 실패:", error);
      } finally {
        setTimeseriesLoading(false);
      }
    };

    fetchTimeseriesData();
  }, [reportData.test_history_id]);

  // 리소스 데이터 가져오기
  useEffect(() => {
    const fetchResourceData = async () => {
      if (!reportData.test_history_id) return;

      setResourceLoading(true);
      try {
        const res = await getTestHistoryResourceSummary(reportData.test_history_id);
        setResourceData(res.data.data);
      } catch (error) {
        console.error("리소스 데이터 조회 실패:", error);
      } finally {
        setResourceLoading(false);
      }
    };

    fetchResourceData();
  }, [reportData.test_history_id]);

  // 요약 데이터 가져오기
  useEffect(() => {
    const fetchAnalysisData = async () => {
      if (!reportData.test_history_id) return;

      setAnalysisLoading(true);
      try {
        const res = await getAnalysisHistory(reportData.test_history_id);
        setAnalysisData(res.data?.analyses || null);
      } catch (error) {
        console.error("분석 데이터 조회 실패:", error);
      } finally {
        setAnalysisLoading(false);
      }
    };

    fetchAnalysisData();
  }, [reportData.test_history_id]);

  const formatDateOnly = (dateString: string) => {
    return new Date(dateString)
      .toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      })
      .replace(/\//g, ".");
  };

  const formatNumber = (num: number, decimals: number = 2) => {
    return num.toFixed(decimals);
  };

  const toPercent = (v: number | string | null | undefined) => {
    if (v == null) return null;
    const num =
      typeof v === "string" ? parseFloat(v.replace("%", "").trim()) : v;
    if (Number.isNaN(num)) return null;
    return num <= 1 ? num * 100 : num;
  };

  const handleTextClick = (key: string, text: string) => {
    if (isEditing && onTextSelect) {
      onTextSelect(key, text);
    }
  };

  const getEditableText = (key: string, defaultText: string) => {
  // reportConfig.editableTexts에 키가 존재하는지 먼저 확인
    if (reportConfig.editableTexts && key in reportConfig.editableTexts) {
      return reportConfig.editableTexts[key];
    }
    // editableTexts에 키가 존재하는지 확인
    if (editableTexts && key in editableTexts) {
      return editableTexts[key];
    }
    // 둘 다 없으면 기본값 반환
    return defaultText;
  };

  const renderEditableBlock = (opts: {
    keyName: string;
    defaultText: string;
    className: string;
  }) => {
    const {keyName, defaultText, className} = opts;
    const value = getEditableText(keyName, defaultText);

    if (isEditing && selectedTextKey === keyName) {
      return (
        <InputField
          title=""
          value={value}
          onChange={(val) => onEditText?.(keyName, val)}
          placeholder="내용을 입력하세요"
          multiline
          showClearButton={true}
          onClear={() => {
            // 빈 문자열로 명시적 설정
            onEditText?.(keyName, "");
          }}
          className={className}
        />
      );
    }

    // 편집 모드일 때 클릭 가능한 텍스트에 적절한 스타일 적용
    const editableClassName = isEditing 
      ? `${className} ${styles.editableText}` 
      : className;

    return (
      <div 
        className={editableClassName} 
        onClick={() => handleTextClick(keyName, value)}
        style={{ cursor: isEditing ? 'pointer' : 'default' }}
      >
        {value}
      </div>
    );
  };

  // 시계열 데이터를 차트 형태로 변환하는 함수
  const prepareChartData = (data: Array<any>) => {
    return data.map((item, index) => {
      const time = new Date(item.timestamp);
      const minutes = String(Math.floor((index * 5) / 60)).padStart(2, "0");
      const seconds = String((index * 5) % 60).padStart(2, "0");

      const result: any = {
        time: `${minutes}:${seconds}`,
        timestamp: item.timestamp,
      };

      // 모든 메트릭을 동적으로 추가
      Object.keys(item).forEach((key) => {
        if (key !== "timestamp") {
          if (key.includes("response_time")) {
            // 응답시간 메트릭은 ms를 초로 변환
            result[key] = item[key] / 1000;
          } else {
            result[key] = item[key];
          }
        }
      });

      return result;
    });
  };

  const getAnalysisSummary = (analysisType: string) => {
    if (!analysisData) return null;
    const analysis = analysisData.find(item => item.analysis_type === analysisType);
    return analysis?.summary || null;
  };

  // 그룹 1: TPS, Error Rate, VUS 차트 시리즈 생성
  const createGroup1ChartSeries = () => {
    return [
      {
        key: "tps",
        name: "TPS (Transactions per Second)",
        color: "#8884d8",
        unit: "req/s",
        yAxis: "left" as const,
      },
      {
        key: "error_rate",
        name: "Error Rate",
        color: "#ff7300",
        unit: "%",
        yAxis: "right" as const,
      },
      {
        key: "vus",
        name: "Virtual Users",
        color: "#dee2e6",
        unit: "users",
        yAxis: "right" as const,
      },
    ];
  };

  // 그룹 2: VUS, Average Response Time, P95 Response Time, P99 Response Time 차트 시리즈 생성
  const createGroup2ChartSeries = () => {
    return [
      {
        key: "vus",
        name: "Virtual Users",
        color: "#dee2e6",
        unit: "users",
        yAxis: "right" as const,
      },
      {
        key: "avg_response_time",
        name: "Average Response Time",
        color: "#82ca9d",
        unit: "sec",
        yAxis: "left" as const,
      },
      {
        key: "p95_response_time",
        name: "P95 Response Time",
        color: "#ffc658",
        unit: "sec",
        yAxis: "left" as const,
      },
      {
        key: "p99_response_time",
        name: "P99 Response Time",
        color: "#ff7c7c",
        unit: "sec",
        yAxis: "left" as const,
      },
    ];
  };

  return (
    <div className={styles.container}>
      <div className={styles.actions}></div>
      <div className={styles.documentPreview} data-pdf-capture>
        <div className={styles.documentHeader}>
          {isEditing ? (
            <InputField
              title="보고서 제목"
              value={reportConfig.customTitle || ""}
              onChange={(val) => onEditText?.("customTitle", val)}
              placeholder="성능 테스트 리포트"
              showClearButton
            />
          ) : (
            <div className="HeadingL">
              {reportConfig.customTitle || "성능 테스트 리포트"}
            </div>
          )}
          <div className={styles.reportDataContainer}>
            <div className={`${styles.reportDate} Body`}>
              작성일: {formatDateOnly(new Date().toISOString())}
            </div>
            <div className={styles.reportLogo}>
              <Logo className={styles.logoIcon} />
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            1. 테스트 대상 소개
          </div>
          <div className={styles.sectionContent}>
            {renderEditableBlock({
              keyName: "testTarget",
              defaultText:
                reportData.description ||
                "테스트 대상에 대한 설명이 제공되지 않았습니다.",
              className: `${styles.contentText} Body`,
            })}
          </div>
        </div>

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            2. 비 기능 테스트 시나리오
          </div>
          <div className={styles.sectionContent}>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>가. 테스트 조건</div>
              <div className={styles.textGroup}>
                {renderEditableBlock({
                  keyName: "testCondition",
                  defaultText: [
                    reportData.scenarios && reportData.scenarios.length > 0
                      ? `${reportData.scenarios
                          .map(
                            (s) => s.endpoint.summary || s.endpoint.description
                          )
                          .join(", ")} 동시 호출 기준으로 테스트`
                      : "테스트 시나리오 정보를 확인할 수 없습니다.",
                    `가상사용자 : 사용자 수 ${
                      reportData.overall?.vus?.max
                        ? `${reportData.overall.vus.max}명`
                        : "정보 없음"
                    }에 대해서 테스트`,
                    `지속 시간: ${
                      reportData.overall?.test_duration
                        ? `${reportData.overall.test_duration}초`
                        : "정보 없음"
                    } 동안 테스트`,
                  ].join("\n"), // ← 점 없이 순수 줄바꿈
                  className: `${styles.contentText} Body`,
                })}
              </div>
            </div>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                나. 테스트 결과 분석 절차
              </div>
              <div className={styles.textGroup}>
                {renderEditableBlock({
                  keyName: "analysisProc",
                  defaultText: [
                    "요청 처리율, 응답 속도, 에러율에 대해서 목표 설정",
                    "테스트 결과와 에러율 비교, 목표 달성 분석",
                    "테스트 대상 자원 사용량 분석",
                  ].join("\n"),
                  className: `${styles.contentText} Body`,
                })}
              </div>
            </div>

            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 2-1. 비기능 테스트 목표
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>테스트 시나리오</th>
                    <th>응답시간(sec)</th>
                    <th>TPS</th>
                    <th>에러율</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.scenarios && reportData.scenarios.length > 0 ? (
                    reportData.scenarios.map((scenario, index) => (
                      <tr key={index}>
                        <td>{scenario.name}</td>
                        <td>{scenario.response_time_target || "X"}</td>
                        <td>{reportData.overall?.target_tps || "X"}</td>
                        <td>{scenario.error_rate_target ?? "X"}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td>데이터 없음</td>
                      <td>정보 없음</td>
                      <td>정보 없음</td>
                      <td>정보 없음</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            3. 비 기능 테스트 수행 결과
          </div>
          <div className={styles.sectionContent}>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                가. 비 기능 테스트 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 3-1. 비 기능 테스트 수행 결과
                </div>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>테스트 시나리오</th>
                      <th>내용</th>
                      <th>결과</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.scenarios && reportData.scenarios.length > 0 ? (
                      reportData.scenarios.map((scenario, index) => (
                        <tr key={index}>
                          <td>{scenario.name}</td>
                          <td>
                            {scenario.endpoint.description ||
                              scenario.endpoint.summary}
                          </td>
                          <td>
                            가상 사용자 {reportData.overall?.vus?.max || 0}
                            명까지 정상 동작함
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>데이터 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                나. 비 기능 테스트 상세내역
              </div>
              {renderEditableBlock({
                keyName: "testDetails",
                defaultText:
                  "비 기능 테스트의 경우 하드웨어 사양뿐 아니라, OS 및 애플리케이션 구성에 따라 성능 측정 결과가 상이하므로, 실제 운영 환경에서 적용할 경우 테스트 결과가 다를 수 있다.",
                className: `${styles.contentText} Body`,
              })}
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>종합분석</div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 3-2. 가상 사용자 {reportData.overall?.vus?.max || 0}명
                </div>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>상태</th>
                      <th>평균시간/sec</th>
                      <th>최소시간/sec</th>
                      <th>TPS</th>
                      <th>에러율</th>
                      <th>총 요청 횟수</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.scenarios && reportData.scenarios.length > 0 ? (
                      reportData.scenarios.map((scenario, index) => (
                        <tr key={index}>
                          <td>{scenario.endpoint.summary}</td>
                          <td>
                            {formatNumber(scenario.response_time.avg / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.min / 1000, 3)}
                          </td>
                          <td>{scenario.tps.avg}</td>
                          <td>
                            {formatNumber(
                              toPercent(scenario.error_rate.avg) ?? 0,
                              1
                            )}
                            %
                          </td>
                          <td>{scenario.total_requests}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>데이터 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* 종합분석 요약 */}
              {getAnalysisSummary('comprehensive') && (
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                {renderEditableBlock({
                  keyName: "comprehensiveAnalysis",
                  defaultText: getAnalysisSummary('comprehensive'),
                  className: `${styles.contentText} Body`,
                })}
              </div>
            )}

              {/* 전체 그래프 추가 - 그룹 1: TPS, Error Rate, VUS */}
              {reportConfig.includeCharts &&
                timeseriesData?.overall?.data &&
                timeseriesData.overall.data.length > 0 && (
                  <div className={styles.tableContainer}>
                    <div className={`${styles.tableTitle} CaptionLight`}>
                      그래프 3-1. 전체 테스트 시계열 분석 1 (TPS, Error Rate,
                      VUS)
                    </div>
                    <MetricChart
                      title="전체 테스트 성능 지표 1"
                      data={prepareChartData(timeseriesData.overall.data)}
                      combinedSeries={createGroup1ChartSeries()}
                      height={400}
                      hideTitle={true}
                      hideControls={true}
                      showLegend={true}
                    />
                  </div>
                )}

              {/* 전체 그래프 추가 - 그룹 2: VUS, Response Times */}
              {reportConfig.includeCharts &&
                timeseriesData?.overall?.data &&
                timeseriesData.overall.data.length > 0 && (
                  <div className={styles.tableContainer}>
                    <div className={`${styles.tableTitle} CaptionLight`}>
                      그래프 3-2. 전체 테스트 시계열 분석 2 (VUS, Response
                      Times)
                    </div>
                    <MetricChart
                      title="전체 테스트 성능 지표 2"
                      data={prepareChartData(timeseriesData.overall.data)}
                      combinedSeries={createGroup2ChartSeries()}
                      height={400}
                      hideTitle={true}
                      hideControls={true}
                      showLegend={true}
                    />
                  </div>
                )}

              {/* 시나리오별 그래프 추가 - 그룹 1과 그룹 2로 분리 */}
              {reportConfig.includeCharts &&
                timeseriesData?.scenarios &&
                timeseriesData.scenarios.map((scenario, index) => {
                  if (!scenario.data || scenario.data.length === 0) return null;

                  return (
                    <React.Fragment key={index}>
                      {/* 그룹 1: TPS, Error Rate, VUS */}
                      <div className={styles.tableContainer}>
                        <div className={`${styles.tableTitle} CaptionLight`}>
                          그래프 3-{3 + index * 2}. {scenario.scenario_name}{" "}
                          시계열 분석 1 (TPS, Error Rate, VUS)
                        </div>
                        <MetricChart
                          title={`${scenario.scenario_name} - ${scenario.endpoint_summary} 1`}
                          data={prepareChartData(scenario.data)}
                          combinedSeries={createGroup1ChartSeries()}
                          height={400}
                          hideTitle={true}
                          hideControls={true}
                          showLegend={true}
                        />
                      </div>

                      {/* 그룹 2: VUS, Response Times */}
                      <div className={styles.tableContainer}>
                        <div className={`${styles.tableTitle} CaptionLight`}>
                          그래프 3-{4 + index * 2}. {scenario.scenario_name}{" "}
                          시계열 분석 2 (VUS, Response Times)
                        </div>
                        <MetricChart
                          title={`${scenario.scenario_name} - ${scenario.endpoint_summary} 2`}
                          data={prepareChartData(scenario.data)}
                          combinedSeries={createGroup2ChartSeries()}
                          height={400}
                          hideTitle={true}
                          hideControls={true}
                          showLegend={true}
                        />
                      </div>
                    </React.Fragment>
                  );
                })}
            </div>

            {/* 나머지 섹션들은 기존과 동일... */}
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                응답시간 상세 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 3-3. 가상 사용자 {reportData.overall?.vus?.max || 0}명
                </div>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>테스트 시나리오</th>
                      <th>평균 응답시간/sec</th>
                      <th>최소 응답시간/sec</th>
                      <th>최대 응답시간/sec</th>
                      <th>p50</th>
                      <th>p95</th>
                      <th>p99</th>
                      <th>목표 응답시간</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.scenarios && reportData.scenarios.length > 0 ? (
                      reportData.scenarios.map((scenario, index) => (
                        <tr key={index}>
                          <td>{scenario.name}</td>
                          <td>
                            {formatNumber(scenario.response_time.avg / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.min / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.max / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.p50 / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.p95 / 1000, 3)}
                          </td>
                          <td>
                            {formatNumber(scenario.response_time.p99 / 1000, 3)}
                          </td>
                          <td>
                            {scenario.response_time_target
                              ? `${formatNumber(scenario.response_time_target / 1000, 3)}초`
                              : "X"}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>데이터 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th>전체</th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.avg / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.min / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.max / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.p50 / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.p95 / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + s.response_time.p99 / 1000,
                            0
                          ) / reportData.scenarios.length,
                          3
                        )}
                      </th>
                      <th></th>
                    </tr>
                  </tfoot>
                </table>
              </div>
              {/* 응답시간 요약 */}
              {getAnalysisSummary('response_time') && (
                <div className={styles.summaryBox}>
                  <div className={`${styles.summaryHeader} Body`}>
                    <Sparkle className={styles.icon} />
                    <span>요약</span>
                  </div>
                  {renderEditableBlock({
                    keyName: "responseTimeSummary",
                    defaultText: getAnalysisSummary('response_time'),
                    className: `${styles.contentText} Body`,
                  })}
                </div>
              )}
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>TPS 상세 결과</div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 3-4. 가상 사용자 {reportData.overall?.vus?.max || 0}명
                </div>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>테스트 시나리오</th>
                      <th>평균 TPS</th>
                      <th>최소 TPS</th>
                      <th>최대 TPS</th>
                      <th>총 요청 수</th>
                      <th>목표</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.scenarios && reportData.scenarios.length > 0 ? (
                      reportData.scenarios.map((scenario, index) => (
                        <tr key={index}>
                          <td>{scenario.name}</td>
                          <td>{formatNumber(scenario.tps.avg, 2)}</td>
                          <td>{scenario.tps.min}</td>
                          <td>{scenario.tps.max}</td>
                          <td>{scenario.total_requests}</td>
                          <td>{reportData.overall?.target_tps || "X"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>데이터 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th>전체</th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) => sum + (s.tps.avg ?? 0),
                            0
                          ),
                          2
                        )}
                      </th>
                      <th>
                        {reportData.scenarios.reduce(
                          (sum, s) => sum + (s.tps.min ?? 0),
                          0
                        )}
                      </th>
                      <th>
                        {reportData.scenarios.reduce(
                          (sum, s) => sum + (s.tps.max ?? 0),
                          0
                        )}
                      </th>
                      <th>
                        {reportData.scenarios.reduce(
                          (sum, s) => sum + (s.total_requests ?? 0),
                          0
                        )}
                      </th>
                      <th></th>
                    </tr>
                  </tfoot>
                </table>
              </div>
              {/* TPS 요약 */}
              {getAnalysisSummary('tps') && (
                <div className={styles.summaryBox}>
                  <div className={`${styles.summaryHeader} Body`}>
                    <Sparkle className={styles.icon} />
                    <span>요약</span>
                  </div>
                  {renderEditableBlock({
                    keyName: "tpsSummary", 
                    defaultText: getAnalysisSummary('tps'),
                    className: `${styles.contentText} Body`,
                  })}
                </div>
              )}
            </div>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                에러율 상세 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 3-5. 가상 사용자 {reportData.overall?.vus?.max || 0}명
                </div>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>테스트 시나리오</th>
                      <th>평균 에러율(%)</th>
                      <th>최소 에러율(%)</th>
                      <th>최대 에러율(%)</th>
                      <th>목표</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.scenarios && reportData.scenarios.length > 0 ? (
                      reportData.scenarios.map((scenario, index) => (
                        <tr key={index}>
                          <td>{scenario.name}</td>
                          <td>
                            {formatNumber(
                              toPercent(scenario.error_rate.avg) ?? 0,
                              1
                            )}
                            %
                          </td>
                          <td>
                            {formatNumber(
                              toPercent(scenario.error_rate.min) ?? 0,
                              1
                            )}
                            %
                          </td>
                          <td>
                            {formatNumber(
                              toPercent(scenario.error_rate.max) ?? 0,
                              1
                            )}
                            %
                          </td>
                          <td>
                            {scenario.error_rate_target != null
                              ? `${formatNumber(
                                  toPercent(scenario.error_rate_target) ?? 0,
                                  1
                                )}%`
                              : "X"}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td>데이터 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                        <td>정보 없음</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th>전체</th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) =>
                              sum + (toPercent(s.error_rate.avg) ?? 0),
                            0
                          ) / reportData.scenarios.length,
                          1
                        )}
                        %
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) =>
                              sum + (toPercent(s.error_rate.min) ?? 0),
                            0
                          ) / reportData.scenarios.length,
                          1
                        )}
                        %
                      </th>
                      <th>
                        {formatNumber(
                          reportData.scenarios.reduce(
                            (sum, s) =>
                              sum + (toPercent(s.error_rate.max) ?? 0),
                            0
                          ) / reportData.scenarios.length,
                          1
                        )}
                        %
                      </th>
                      <th></th>
                    </tr>
                  </tfoot>
                </table>
              </div>
              {/* 에러율 요약 */}
              {getAnalysisSummary('error_rate') && (
                <div className={styles.summaryBox}>
                  <div className={`${styles.summaryHeader} Body`}>
                    <Sparkle className={styles.icon} />
                    <span>요약</span>
                  </div>
                  {renderEditableBlock({
                    keyName: "errorRateSummary",
                    defaultText: getAnalysisSummary('error_rate'),
                    className: `${styles.contentText} Body`,
                  })}
                </div>
              )}
            </div>
            <div className={`${styles.subTitle} TitleS`}>
              다. 자원 사용량 분석
            </div>
            {/* CPU 사용량 테이블 */}
            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 3-6. 서버별 CPU 사용량
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>서버 유형</th>
                    <th>최소 사용량(%)</th>
                    <th>평균 사용량(%)</th>
                    <th>최대 사용량(%)</th>
                  </tr>
                </thead>
                <tbody>
                  {resourceData && resourceData.length > 0 ? (
                    resourceData.map((resource, index) => (
                      <tr key={index}>
                        <td>
                          {resource.service_type === 'SERVER' ? 'Backend' : 'DB Server'}
                        </td>
                        <td>
                          {formatNumber(resource.cpu_usage_summary.percent.min, 1)}%
                        </td>
                        <td>
                          {formatNumber(resource.cpu_usage_summary.percent.avg, 1)}%
                        </td>
                        <td>
                          {formatNumber(resource.cpu_usage_summary.percent.max, 1)}%
                        </td>
                      </tr>
                    ))
                  ) : (
                    <>
                      <tr>
                        <td>Backend</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                      </tr>
                      <tr>
                        <td>DB Server</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Memory 사용량 테이블 */}
            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 3-7. 서버별 Memory 사용량
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>서버 유형</th>
                    <th>최소 사용량(%)</th>
                    <th>평균 사용량(%)</th>
                    <th>최대 사용량(%)</th>
                  </tr>
                </thead>
                <tbody>
                  {resourceData && resourceData.length > 0 ? (
                    resourceData.map((resource, index) => (
                      <tr key={index}>
                        <td>
                          {resource.service_type === 'SERVER' ? 'Backend' : 'DB Server'}
                        </td>
                        <td>
                          {formatNumber(resource.memory_usage_summary.percent.min, 1)}%
                        </td>
                        <td>
                          {formatNumber(resource.memory_usage_summary.percent.avg, 1)}%
                        </td>
                        <td>
                          {formatNumber(resource.memory_usage_summary.percent.max, 1)}%
                        </td>
                      </tr>
                    ))
                  ) : (
                    <>
                      <tr>
                        <td>Backend</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                      </tr>
                      <tr>
                        <td>DB Server</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
            {/* 자원 사용량 요약 */}
            {getAnalysisSummary('resource_usage') && (
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                {renderEditableBlock({
                  keyName: "resourceSummary",
                  defaultText: getAnalysisSummary('resource_usage'),
                  className: `${styles.contentText} Body`,
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;