import React from "react";
import styles from "./ReportViewer.module.css";
import { Download } from "lucide-react";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import PDFDocument from "./PDFDocument";
import { Button } from "../Button/Button";
import { PDFDownloadLink, PDFViewer } from "@react-pdf/renderer";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  isPreview?: boolean;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  reportData,
  reportConfig,
  isPreview = false
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatNumber = (num: number, decimals: number = 2) => {
    return num.toFixed(decimals);
  };

  return (
    <div className={styles.container}>
        <div className={styles.actions}>
            {!isPreview && (
                <PDFDownloadLink
                document={<PDFDocument reportData={reportData} reportConfig={reportConfig} />}
                fileName={`${reportConfig.customTitle || '성능테스트리포트'}_${new Date().toISOString().split('T')[0]}.pdf`}
                >
                {({ loading }) => (
                    <Button
                        icon={<Download />}
                    >
                        {loading ? 'PDF 생성 중...' : '다운로드'}
                    </Button>
                )}
                </PDFDownloadLink>
            )}
        </div>

      {isPreview ? (
        <div className={styles.previewContainer}>
          <div className={styles.documentPreview}>
            <div className={styles.documentHeader}>
              <h1>{reportConfig.customTitle || '성능 테스트 리포트'}</h1>
              {reportConfig.companyName && (
                <div className={styles.companyName}>{reportConfig.companyName}</div>
              )}
              {reportConfig.reporterName && (
                <div className={styles.reporterName}>작성자: {reportConfig.reporterName}</div>
              )}
              <div className={styles.reportDate}>
                작성일: {formatDate(new Date().toISOString())}
              </div>
            </div>

            {reportConfig.includeExecutiveSummary && (
              <div className={styles.section}>
                <h2>요약 정보</h2>
                <div className={styles.summaryGrid}>
                  <div className={styles.summaryItem}>
                    <span className={styles.label}>테스트 상태:</span>
                    <span className={styles.value}>
                      {reportData.is_completed ? '완료' : '진행 중'}
                    </span>
                  </div>
                  <div className={styles.summaryItem}>
                    <span className={styles.label}>총 요청 수:</span>
                    <span className={styles.value}>{reportData.total_requests}개</span>
                  </div>
                  <div className={styles.summaryItem}>
                    <span className={styles.label}>실패 요청 수:</span>
                    <span className={styles.value}>{reportData.failed_requests}개</span>
                  </div>
                  <div className={styles.summaryItem}>
                    <span className={styles.label}>에러율:</span>
                    <span className={styles.value}>{formatNumber(reportData.error_rate)}%</span>
                  </div>
                </div>
                <p className={styles.description}>
                  {reportConfig.customDescription}
                </p>
              </div>
            )}

            {reportConfig.includeDetailedMetrics && (
              <div className={styles.section}>
                <h2>상세 메트릭</h2>
                <div className={styles.metricsGrid}>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>실제 TPS</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.actual_tps)}</div>
                  </div>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>평균 응답시간</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.avg_response_time)}ms</div>
                  </div>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>최대 응답시간</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.max_response_time)}ms</div>
                  </div>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>최소 응답시간</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.min_response_time)}ms</div>
                  </div>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>P95 응답시간</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.p95_response_time)}ms</div>
                  </div>
                  <div className={styles.metric}>
                    <div className={styles.metricLabel}>테스트 지속시간</div>
                    <div className={styles.metricValue}>{formatNumber(reportData.test_duration)}초</div>
                  </div>
                </div>
              </div>
            )}

            {reportConfig.includeScenarioBreakdown && reportData.scenarios && (
              <div className={styles.section}>
                <h2>시나리오 분석</h2>
                {reportData.scenarios.map((scenario, index) => (
                  <div key={scenario.id} className={styles.scenarioCard}>
                    <h3>시나리오 {index + 1}: {scenario.endpoint.summary}</h3>
                    <div className={styles.scenarioDetails}>
                      <div className={styles.endpointInfo}>
                        <strong>{scenario.endpoint.method}</strong> {scenario.endpoint.path}
                      </div>
                      <p>{scenario.endpoint.description}</p>
                      
                      <div className={styles.scenarioMetrics}>
                        <div className={styles.scenarioMetric}>
                          <span>실제 TPS: {formatNumber(scenario.actual_tps)}</span>
                        </div>
                        <div className={styles.scenarioMetric}>
                          <span>평균 응답시간: {formatNumber(scenario.avg_response_time)}ms</span>
                        </div>
                        <div className={styles.scenarioMetric}>
                          <span>에러율: {formatNumber(scenario.error_rate)}%</span>
                        </div>
                        <div className={styles.scenarioMetric}>
                          <span>총 요청: {scenario.total_requests}개</span>
                        </div>
                      </div>

                      {scenario.stages && scenario.stages.length > 0 && (
                        <div className={styles.stagesInfo}>
                          <h4>부하 단계</h4>
                          {scenario.stages.map((stage, stageIndex) => (
                            <div key={stage.id} className={styles.stage}>
                              단계 {stageIndex + 1}: {stage.duration} 동안 {stage.target} VU
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.pdfContainer}>
          <PDFViewer className={styles.pdfViewer}>
            <PDFDocument reportData={reportData} reportConfig={reportConfig} />
          </PDFViewer>
        </div>
      )}
    </div>
  );
};

export default ReportViewer;