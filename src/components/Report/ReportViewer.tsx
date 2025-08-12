import React from "react";
import styles from "./ReportViewer.module.css";
import {Sparkle} from "lucide-react";
import type {TestData, ReportConfig} from "../../pages/Report/Report";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  reportData,
  reportConfig,
}) => {
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
      typeof v === "string"
        ? parseFloat(v.replace("%", "").trim())
        : v;
    if (Number.isNaN(num)) return null;
    return num <= 1 ? num * 100 : num;
  };

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
              <div className="Body">
                {reportConfig.customDescription ||
                  reportData.description ||
                  "테스트 설명이 제공되지 않았습니다."}
              </div>
            </div>
          </div>
        )}

        <div className={styles.section}>
          <div className={`${styles.sectionTitle} HeadingS`}>
            2. 테스트 대상 소개
          </div>
          <div className={styles.sectionContent}>
            <div className="Body">
              웹 기반의 CRM 솔루션으로 전신은 Centric-CRM 이며, 공식적으로
              데이터베이스는 PostgreSQL 8.x를사용하고, 애플리케이션 서버로는
              Apache Tomcat6.0을 사용함
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
                <div className={`${styles.contentText} Body`}>
                  {reportData.scenarios && reportData.scenarios.length > 0
                    ? `${reportData.scenarios
                        .map(
                          (s) => s.endpoint.summary || s.endpoint.description
                        )
                        .join(", ")} 동시 호출 기준으로 테스트`
                    : "테스트 시나리오 정보를 확인할 수 없습니다."}
                </div>
                <div className={`${styles.contentText} Body`}>
                  가상사용자 : 고정 사용자 수{" "}
                  {reportData.overall?.vus?.max
                    ? `${reportData.overall.vus.max}명`
                    : "정보 없음"}
                  에 대해서 테스트
                </div>
                <div className={`${styles.contentText} Body`}>
                  지속 시간:{" "}
                  {reportData.overall?.test_duration
                    ? `${reportData.overall.test_duration}초`
                    : "정보 없음"}{" "}
                  동안 테스트
                </div>
              </div>
            </div>
            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>
                나. 테스트 결과 분석 절차
              </div>
              <div className={styles.textGroup}>
                <div className={`${styles.contentText} Body`}>
                  요청 처리율, 응답 속도, 에러율에 대해서 목표 설정
                </div>
                <div className={`${styles.contentText} Body`}>
                  테스트 결과와 에러율 비교, 목표 달성 분석
                </div>
                <div className={`${styles.contentText} Body`}>
                  테스트 대상 자원 사용량 분석
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
                  표 4-1. 비기능테스트수행결과
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
              <div className="Body">
                비 기능 테스트의 경우 하드웨어 사양뿐 아니라, OS 및 애플리케이션
                구성에 따라 성능 측정 결과가 상이하므로, 실제 운영 환경에서
                적용할 경우 테스트 결과가 다를 수 있다.
              </div>
            </div>

            <div className={styles.subTitleGroup}>
              <div className={`${styles.subTitle} TitleS`}>종합분석</div>
              <div className={styles.tableContainer}>
                <div className={`${styles.tableTitle} CaptionLight`}>
                  표 4-2. 가상사용자 {reportData.overall?.vus?.max || 0}명
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
                              (toPercent(scenario.error_rate.avg) ?? 0),
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
                </table>
              </div>
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div className={`${styles.summaryContent} Body`}>
                  최소, 평균 응답 시간은 목표를 달성하였으나, P95의 경우 약간 못
                  미치는 결과 발생하였음. 약 92% 사용자에게 원활한 서비스 제공
                  가능할 것으로 예상.
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
                </table>
              </div>
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div className={`${styles.summaryContent} Body`}>
                  테스트 시나리오별 TPS는 참고값으로만 사용하며, 전체 TPS에
                  대해서 목표를 비교하였음. 전체 평균 TPS는 목표에 거의 유사하게
                  근접하였음. (TPS의 경우 테스트 초반 가상 사용자 수가 부족한
                  경우도 존재. 최소 TPS에 대해서는 참고값으로만 사용하였음.)
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
                              (toPercent(scenario.error_rate.avg) ?? 0),
                              1
                            )}
                            %
                          </td>
                          <td>
                            {formatNumber(
                              (toPercent(scenario.error_rate.min) ?? 0),
                              1
                            )}
                            %
                          </td>
                          <td>
                            {formatNumber(
                              (toPercent(scenario.error_rate.max) ?? 0),
                              1
                            )}
                            %
                          </td>
                          <td>
                            {scenario.error_rate_target != null
                              ? `${formatNumber(
                                  (toPercent(scenario.error_rate_target) ?? 0),
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
                </table>
              </div>
              <div className={styles.summaryBox}>
                <div className={`${styles.summaryHeader} Body`}>
                  <Sparkle className={styles.icon} />
                  <span>요약</span>
                </div>
                <div className={`${styles.summaryContent} Body`}>
                  대부분의 경우 목표 에러율보다 안정적이었으나, 최대 에러율의
                  경우 목표치보다 높은 것으로 추정. 요청 수가 많아질 때 시스템
                  위험성을 고려해야 함.
                </div>
              </div>
            </div>
            <div className={`${styles.subTitle} TitleS`}>
              다. 자원 사용량 분석
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;
