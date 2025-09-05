import React, { useEffect, useState } from "react";
import styles from "./ReportViewer.module.css";
import { Sparkle } from "lucide-react";
import type { TestData, ReportConfig } from "../../pages/Report/Report";
import MetricChart from "../MetricChart/MetricChart";
import { getTestHistoryTimeseries } from "../../api";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  isEditing?: boolean;
  selectedTextKey?: string;
  editableTexts?: Record<string, string>;
  onTextSelect?: (key: string, text: string) => void;
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
}) => {
  const [timeseriesData, setTimeseriesData] = useState<TimeseriesData | null>(null);
  const [timeseriesLoading, setTimeseriesLoading] = useState<boolean>(false);

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
    // reportConfig에서 먼저 확인하고, 없으면 editableTexts에서 확인
    return reportConfig.editableTexts?.[key] || editableTexts?.[key] || defaultText;
  };

  const getTextClassName = (baseClass: string, key: string) => {
    const classes = [baseClass];
    if (isEditing) {
      classes.push(styles.editableText);
      if (selectedTextKey === key) {
        classes.push(styles.selectedText);
      }
    }
    return classes.join(' ');
  };

  // 시계열 데이터를 차트 형태로 변환하는 함수
  const prepareChartData = (data: Array<any>) => {
    return data.map((item, index) => {
      const time = new Date(item.timestamp);
      const minutes = String(Math.floor(index * 10 / 60)).padStart(2, '0');
      const seconds = String((index * 10) % 60).padStart(2, '0');
      
      return {
        time: `${minutes}:${seconds}`,
        avg_response_time: item.avg_response_time / 1000, // ms to seconds
        tps: item.tps,
        error_rate: item.error_rate,
        bytes_per_second: item.tps * 1024, // TPS를 Bytes per Second로 근사치 계산
      };
    });
  };

  // 전체 데이터 차트 시리즈 설정
  const overallChartSeries = [
    {
      key: "avg_response_time",
      name: "Average Response Time",
      color: "#8884d8",
      unit: "sec",
      yAxis: "left" as const,
    },
    {
      key: "bytes_per_second",
      name: "Bytes per Second",
      color: "#82ca9d",
      unit: "bytes/s",
      yAxis: "right" as const,
    },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.actions}></div>
      <div className={styles.documentPreview} data-pdf-capture>
        <div className={styles.documentHeader}>
          <div className="HeadingL">
            {reportConfig.customTitle || "성능 테스트 리포트"}
          </div>
          <div className={styles.reportDataContainer}>
            <div className={`${styles.reportDate} Body`}>
              작성일: {formatDateOnly(new Date().toISOString())}
            </div>
            <div className={`${styles.reportLogo} HeadingS`}>● Plog</div>
          </div>
        </div>

        {reportConfig.includeExecutiveSummary && (
          <div className={styles.section}>
            <div className={`${styles.sectionTitle} HeadingS`}>
              1. 요약 정보
            </div>
            <div className={styles.sectionContent}>
              <div 
                className={getTextClassName(`${styles.contentText} Body`, 'executiveSummary')}
                data-editable
                onClick={() => handleTextClick('executiveSummary', reportConfig.customDescription || reportData.description || "테스트 설명이 제공되지 않았습니다.")}
              >
                {getEditableText('executiveSummary', reportConfig.customDescription || reportData.description || "테스트 설명이 제공되지 않았습니다.")}
              </div>
            </div>
          </div>
        )}

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            2. 테스트 대상 소개
          </div>
          <div className={styles.sectionContent}>
            <div 
              className={getTextClassName(`${styles.contentText} Body`, 'testTarget')}
              data-editable
              onClick={() => handleTextClick('testTarget', "웹 기반의 CRM 솔루션으로 전신은 Centric-CRM 이며, 공식적으로 데이터베이스는 PostgreSQL 8.x를사용하고, 애플리케이션 서버로는 Apache Tomcat6.0을 사용함")}
            >
              {getEditableText('testTarget', "웹 기반의 CRM 솔루션으로 전신은 Centric-CRM 이며, 공식적으로 데이터베이스는 PostgreSQL 8.x를사용하고, 애플리케이션 서버로는 Apache Tomcat6.0을 사용함")}
            </div>
          </div>
        </div>

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            3. 비 기능 테스트 시나리오
          </div>
          <div className={styles.sectionContent}>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>가. 테스트 조건</div>
              <div className={styles.textGroup}>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'testCondition1')}
                  data-editable
                  onClick={() => handleTextClick('testCondition1', `${reportData.scenarios && reportData.scenarios.length > 0 ? `${reportData.scenarios.map(s => s.endpoint.summary || s.endpoint.description).join(", ")} 동시 호출 기준으로 테스트` : "테스트 시나리오 정보를 확인할 수 없습니다."}`)}
                >
                  {getEditableText('testCondition1', reportData.scenarios && reportData.scenarios.length > 0 ? `${reportData.scenarios.map(s => s.endpoint.summary || s.endpoint.description).join(", ")} 동시 호출 기준으로 테스트` : "테스트 시나리오 정보를 확인할 수 없습니다.")}
                </div>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'testCondition2')}
                  data-editable
                  onClick={() => handleTextClick('testCondition2', `가상사용자 : 고정 사용자 수 ${reportData.overall?.vus?.max ? `${reportData.overall.vus.max}명` : "정보 없음"}에 대해서 테스트`)}
                >
                  {getEditableText('testCondition2', `가상사용자 : 고정 사용자 수 ${reportData.overall?.vus?.max ? `${reportData.overall.vus.max}명` : "정보 없음"}에 대해서 테스트`)}
                </div>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'testCondition3')}
                  data-editable
                  onClick={() => handleTextClick('testCondition3', `지속 시간: ${reportData.overall?.test_duration ? `${reportData.overall.test_duration}초` : "정보 없음"} 동안 테스트`)}
                >
                  {getEditableText('testCondition3', `지속 시간: ${reportData.overall?.test_duration ? `${reportData.overall.test_duration}초` : "정보 없음"} 동안 테스트`)}
                </div>
              </div>
            </div>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                나. 테스트 결과 분석 절차
              </div>
              <div className={styles.textGroup}>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'analysisProc1')}
                  data-editable
                  onClick={() => handleTextClick('analysisProc1', "요청 처리율, 응답 속도, 에러율에 대해서 목표 설정")}
                >
                  {getEditableText('analysisProc1', "요청 처리율, 응답 속도, 에러율에 대해서 목표 설정")}
                </div>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'analysisProc2')}
                  data-editable
                  onClick={() => handleTextClick('analysisProc2', "테스트 결과와 에러율 비교, 목표 달성 분석")}
                >
                  {getEditableText('analysisProc2', "테스트 결과와 에러율 비교, 목표 달성 분석")}
                </div>
                <div 
                  className={getTextClassName(`${styles.contentText} Body`, 'analysisProc3')}
                  data-editable
                  onClick={() => handleTextClick('analysisProc3', "테스트 대상 자원 사용량 분석")}
                >
                  {getEditableText('analysisProc3', "테스트 대상 자원 사용량 분석")}
                </div>
              </div>
            </div>

            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 3-1. 비기능 테스트 시나리오
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>테스트 시나리오</th>
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
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td>데이터 없음</td>
                      <td>정보 없음</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 3-2. 비기능 테스트 목표
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
            4. 비 기능 테스트 수행 결과
          </div>
          <div className={styles.sectionContent}>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                가. 비 기능 테스트 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-1. 비 기능 테스트 수행 결과
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
              <div 
                className={getTextClassName(`${styles.contentText} Body`, 'testDetails')}
                data-editable
                onClick={() => handleTextClick('testDetails', "비 기능 테스트의 경우 하드웨어 사양뿐 아니라, OS 및 애플리케이션 구성에 따라 성능 측정 결과가 상이하므로, 실제 운영 환경에서 적용할 경우 테스트 결과가 다를 수 있다.")}
              >
                {getEditableText('testDetails', "비 기능 테스트의 경우 하드웨어 사양뿐 아니라, OS 및 애플리케이션 구성에 따라 성능 측정 결과가 상이하므로, 실제 운영 환경에서 적용할 경우 테스트 결과가 다를 수 있다.")}
              </div>
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>종합분석</div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-2. 가상 사용자 {reportData.overall?.vus?.max || 0}명
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

              {/* 전체 그래프 추가 */}
              {reportConfig.includeCharts && timeseriesData?.overall?.data && timeseriesData.overall.data.length > 0 && (
                <div className={styles.tableContainer}>
                  <div className={`${styles.tableTitle} CaptionLight`}>
                    그래프 4-1. 전체 테스트 시계열 분석
                  </div>
                  <MetricChart
                    title="전체 테스트 성능 지표"
                    data={prepareChartData(timeseriesData.overall.data)}
                    combinedSeries={overallChartSeries}
                    height={300}
                    hideTitle={true}
                    hideControls={true}
                  />
                </div>
              )}

              {/* 시나리오별 그래프 추가 */}
              {reportConfig.includeCharts && timeseriesData?.scenarios && timeseriesData.scenarios.map((scenario, index) => {
                if (!scenario.data || scenario.data.length === 0) return null;
                
                return (
                  <div key={index} className={styles.tableContainer}>
                    <div className={`${styles.tableTitle} CaptionLight`}>
                      그래프 4-{index + 2}. {scenario.scenario_name} 시계열 분석
                    </div>
                    <MetricChart
                      title={`${scenario.scenario_name} - ${scenario.endpoint_summary}`}
                      data={prepareChartData(scenario.data)}
                      combinedSeries={overallChartSeries}
                      height={300}
                      hideTitle={true}
                      hideControls={true}
                    />
                  </div>
                );
              })}
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                응답시간 상세 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-3. 가상 사용자 {reportData.overall?.vus?.max || 0}명
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
                            {formatNumber(
                              scenario.response_time.avg / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {formatNumber(
                              scenario.response_time.min / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {formatNumber(
                              scenario.response_time.max / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {formatNumber(
                              scenario.response_time.p50 / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {formatNumber(
                              scenario.response_time.p95 / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {formatNumber(
                              scenario.response_time.p99 / 1000,
                              3
                            )}
                          </td>
                          <td>
                            {scenario.response_time_target
                              ? `${scenario.response_time_target}초`
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
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div 
                  className={getTextClassName(`${styles.summaryContent} Body`, 'responseTimeSummary')}
                  data-editable
                  onClick={() => handleTextClick('responseTimeSummary', "최소, 평균 응답 시간은 목표를 달성하였으나, P95의 경우 약간 못 미치는 결과 발생하였음. 약 92% 사용자에게 원활한 서비스 제공 가능할 것으로 예상.")}
                >
                  {getEditableText('responseTimeSummary', "최소, 평균 응답 시간은 목표를 달성하였으나, P95의 경우 약간 못 미치는 결과 발생하였음. 약 92% 사용자에게 원활한 서비스 제공 가능할 것으로 예상.")}
                </div>
              </div>
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>TPS 상세 결과</div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-4. 가상 사용자 {reportData.overall?.vus?.max || 0}명
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
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div 
                  className={getTextClassName(`${styles.summaryContent} Body`, 'tpsSummary')}
                  data-editable
                  onClick={() => handleTextClick('tpsSummary', "테스트 시나리오별 TPS는 참고값으로만 사용하며, 전체 TPS에 대해서 목표를 비교하였음. 전체 평균 TPS는 목표에 거의 유사하게 근접하였음. (TPS의 경우 테스트 초반 가상 사용자 수가 부족한 경우도 존재. 최소 TPS에 대해서는 참고값으로만 사용하였음.)")}
                >
                  {getEditableText('tpsSummary', "테스트 시나리오별 TPS는 참고값으로만 사용하며, 전체 TPS에 대해서 목표를 비교하였음. 전체 평균 TPS는 목표에 거의 유사하게 근접하였음. (TPS의 경우 테스트 초반 가상 사용자 수가 부족한 경우도 존재. 최소 TPS에 대해서는 참고값으로만 사용하였음.)")}
                </div>
              </div>
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                에러율 상세 결과
              </div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-5. 가상 사용자 {reportData.overall?.vus?.max || 0}명
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
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div 
                  className={getTextClassName(`${styles.summaryContent} Body`, 'errorRateSummary')}
                  data-editable
                  onClick={() => handleTextClick('errorRateSummary', "대부분의 경우 목표 에러율보다 안정적이었으나, 최대 에러율의 경우 목표치보다 높은 것으로 추정. 요청 수가 많아질 때 시스템 위험성을 고려해야 함.")}
                >
                  {getEditableText('errorRateSummary', "대부분의 경우 목표 에러율보다 안정적이었으나, 최대 에러율의 경우 목표치보다 높은 것으로 추정. 요청 수가 많아질 때 시스템 위험성을 고려해야 함.")}
                </div>
              </div>
            </div>
            <div className={`${styles.subTitle} TitleS`}>
              다. 자원 사용량 분석
            </div>
            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 서버별 CPU 사용량
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th></th>
                    <th>최소 사용량</th>
                    <th>평균 사용량</th>
                    <th>최대 사용량</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Backend</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                  </tr>

                  <tr>
                    <td>DB Server</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className={styles.tableContainer}>
              <div className={`${styles.tableTitle} CaptionLight`}>
                표 서버별 Memory 사용량
              </div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th></th>
                    <th>최소 사용량</th>
                    <th>평균 사용량</th>
                    <th>최대 사용량</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Backend</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                  </tr>

                  <tr>
                    <td>DB Server</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                    <td>0.0%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className={styles.summaryBox}>
              <div className={`${styles.summaryHeader} Body`}>
                <Sparkle className={styles.icon} />
                <span>요약</span>
              </div>
              <div 
                className={getTextClassName(`${styles.summaryContent} Body`, 'resourceSummary')}
                data-editable
                onClick={() => handleTextClick('resourceSummary', "테스트 결과 백엔드 서버의 CPU 사용량이 최대 100%에 도달하며 높은 부하를 보였으나, DB 서버의 CPU 및 메모리 사용량은 여유가 있었습니다. 이는 서비스 병목 현상이 백엔드 서버의 CPU에 있음을 나타냅니다. 따라서 백엔드 서버의 스케일 아웃을 통해 성능 향상 및 안정성을 확보할 필요가 있습니다.")}
              >
                {getEditableText('resourceSummary', "테스트 결과 백엔드 서버의 CPU 사용량이 최대 100%에 도달하며 높은 부하를 보였으나, DB 서버의 CPU 및 메모리 사용량은 여유가 있었습니다. 이는 서비스 병목 현상이 백엔드 서버의 CPU에 있음을 나타냅니다. 따라서 백엔드 서버의 스케일 아웃을 통해 성능 향상 및 안정성을 확보할 필요가 있습니다.")}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;