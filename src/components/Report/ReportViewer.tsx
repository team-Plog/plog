import React from "react";
import styles from "./ReportViewer.module.css";
import type {TestData, ReportConfig} from "../../pages/Report/Report";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  reportData,
  reportConfig,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDateOnly = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).replace(/\//g, '.');
  };

  const formatNumber = (num: number, decimals: number = 2) => {
    return num.toFixed(decimals);
  };

  return (
    <div className={styles.container}>
      <div className={styles.actions}></div>
        <div className={styles.previewContainer}>
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
                <div className={`${styles.sectionTitle} HeadingS`}>1. 요약 정보</div>
                <div className={styles.sectionContent}>
                  <div className="Body">
                    {reportConfig.customDescription || reportData.description || "테스트 설명이 제공되지 않았습니다."}
                  </div>
                </div>
              </div>
            )}
            
            <div className={styles.section}>
              <div className={`${styles.sectionTitle} HeadingS`}>2. 테스트 대상 소개</div>
              <div className={styles.sectionContent}>
                <div className="Body">
                  웹 기반의 CRM 솔루션으로 전신은 Centric-CRM 이며, 공식적으로
                  데이터베이스는 PostgreSQL 8.x를사용하고, 애플리케이션 서버로는
                  Apache Tomcat6.0을 사용함
                </div>
              </div>
            </div>
            
            <div className={styles.section}>
              <div className={`${styles.sectionTitle} HeadingS`}>3. 비 기능 테스트 시나리오</div>
              <div className={styles.sectionContent}>
                <div className={styles.subTitleGroup}>
                  <div className={`${styles.subTitle} TitleS`}>가. 테스트 조건</div>
                  <div className={styles.textGroup}>
                    <div className={`${styles.contentText} Body`}>
                      {reportData.scenarios && reportData.scenarios.length > 0 
                        ? `${reportData.scenarios.map(s => s.endpoint.summary || s.endpoint.description).join(', ')} 동시 호출 기준으로 테스트`
                        : '테스트 시나리오 정보를 확인할 수 없습니다.'}
                    </div>
                    <div className={`${styles.contentText} Body`}>
                      가상사용자 : 고정 사용자 수 {reportData.overall?.vus?.max ? `${reportData.overall.vus.max}명` : '정보 없음'}에 대해서 테스트
                    </div>
                    <div className={`${styles.contentText} Body`}>
                      지속 시간: {reportData.overall?.test_duration ? `${reportData.overall.test_duration}초` : '정보 없음'} 동안 테스트
                    </div>
                  </div>
                </div>
                <div className={styles.subTitleGroup}>
                  <div className={`${styles.subTitle} TitleS`}>나. 테스트 결과 분석 절차</div>
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
                  <div className={`${styles.tableTitle} CaptionLight`}>표 3-1. 비기능 테스트 시나리오</div>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>테스트 시나리오</th>
                        <th>결과</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.scenarios && reportData.scenarios.length > 0 
                        ? reportData.scenarios.map((scenario, index) => (
                            <tr key={index}>
                              <td>{scenario.name}</td>
                              <td>{scenario.endpoint.description || scenario.endpoint.summary}</td>
                            </tr>
                          ))
                        : (
                            <tr>
                              <td>데이터 없음</td>
                              <td>정보 없음</td>
                            </tr>
                          )
                      }
                    </tbody>
                  </table>
                </div>

                <div className={styles.tableContainer}>
                  <div className={`${styles.tableTitle} CaptionLight`}>표 3-2. 비기능 테스트 목표</div>
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
                      {reportData.scenarios && reportData.scenarios.length > 0 
                        ? reportData.scenarios.map((scenario, index) => (
                            <tr key={index}>
                              <td>{scenario.name}</td>
                              <td>{scenario.response_time_target || 'X'}</td>
                              <td>{reportData.overall?.target_tps || 'X'}</td>
                              <td>{scenario.error_rate_target || 'X'}</td>
                            </tr>
                          ))
                        : (
                            <tr>
                              <td>데이터 없음</td>
                              <td>정보 없음</td>
                              <td>정보 없음</td>
                              <td>정보 없음</td>
                            </tr>
                          )
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            
            <div className={styles.section}>
              <div className={`${styles.sectionTitle} HeadingS`}>4. 기능 테스트 수행 결과</div>
              <div className={styles.sectionContent}>
                <div className={`${styles.contentText} Body`}>
                  기능 테스트 수행 관련 세부 절차 및 결과는 별첨 ⌜Concoursesuite
                  테스트 케이스⌟를 참고한다.
                </div>
                
                <div className={`${styles.subTitle} TitleS`}>가. 기능 테스트 결과</div>
                <div className={`${styles.subTitle} TitleS`}>나. 결함 내역</div>
                <div className={`${styles.subTitle} TitleS`}>다. 특이사항</div>
              </div>
            </div>
            
            <div className={styles.section}>
              <div className={`${styles.sectionTitle} HeadingS`}>5. 비 기능 테스트 수행 결과</div>
              <div className={styles.sectionContent}>
                <div className={`${styles.subTitle} TitleS`}>가. 비 기능 테스트 결과</div>
                <div className={`${styles.subTitle} TitleS`}>나. 비 기능 테스트 상세내역</div>
              </div>
            </div>
          </div>
        </div>
    </div>
  );
};

export default ReportViewer;