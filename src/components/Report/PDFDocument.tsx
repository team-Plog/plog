import React from 'react';
import { Document, Page, Text, View, StyleSheet, Font } from '@react-pdf/renderer';
import type { TestData, ReportConfig } from '../../pages/Report/Report';

interface PDFDocumentProps {
  reportData: TestData;
  reportConfig: ReportConfig;
}

Font.register({
  family: 'Pretendard',
  fonts: [
    {
      src: '/fonts/Pretendard-Medium.otf',
      fontWeight: 500,
    },
    {
      src: '/fonts/Pretendard-SemiBold.otf',
      fontWeight: 600,
    },
    {
      src: '/fonts/Pretendard-Bold.otf',
      fontWeight: 700,
    },
  ],
});

// PDF 스타일 정의
const styles = StyleSheet.create({
  page: {
    fontFamily: 'Pretendard',
    fontSize: 12,
    paddingTop: 35,
    paddingBottom: 65,
    paddingHorizontal: 35,
    lineHeight: 1.5,
  },
  title: {
    fontSize: 32,
    textAlign: 'center',
    marginBottom: 30,
    fontWeight: 700,
    color: '#1a202c',
  },
  subtitle: {
    fontSize: 18,
    marginBottom: 20,
    fontWeight: 600,
    color: '#2d3748',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    paddingBottom: 5,
  },
  companyInfo: {
    textAlign: 'center',
    marginBottom: 20,
    color: '#4a5568',
  },
  companyName: {
    fontSize: 16,
    marginBottom: 5,
    color: '#4a5568',
  },
  reporterName: {
    fontSize: 12,
    marginBottom: 5,
    color: '#4a5568',
  },
  reportDate: {
    fontSize: 10,
    color: '#718096',
  },
  section: {
    marginBottom: 25,
  },
  summaryContainer: {
    backgroundColor: '#f7fafc',
    padding: 15,
    marginBottom: 15,
    borderRadius: 5,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  summaryItem: {
    flex: '1 1 45%',
    minWidth: 200,
    backgroundColor: '#ffffff',
    padding: 10,
    borderRadius: 3,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#3182ce',
  },
  summaryLabel: {
    fontSize: 10,
    color: '#4a5568',
    marginBottom: 2,
    fontWeight: 600,
  },
  summaryValue: {
    fontSize: 14,
    color: '#1a202c',
    fontWeight: 500,
  },
  description: {
    fontSize: 11,
    color: '#4a5568',
    marginTop: 10,
    lineHeight: 1.4,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metric: {
    flex: '1 1 30%',
    minWidth: 150,
    backgroundColor: '#edf2f7',
    padding: 12,
    borderRadius: 5,
    alignItems: 'center',
    marginBottom: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#3182ce',
  },
  metricLabel: {
    fontSize: 9,
    color: '#4a5568',
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 500,
    color: '#1a202c',
  },
  scenarioCard: {
    backgroundColor: '#f7fafc',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 5,
    padding: 15,
    marginBottom: 15,
  },
  scenarioTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#1a202c',
    marginBottom: 10,
  },
  endpointInfo: {
    backgroundColor: '#2d3748',
    color: '#ffffff',
    padding: 8,
    borderRadius: 3,
    fontSize: 10,
    fontFamily: 'Courier',
    marginBottom: 10,
  },
  scenarioDescription: {
    fontSize: 10,
    color: '#4a5568',
    marginBottom: 12,
    lineHeight: 1.3,
  },
  scenarioMetricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  scenarioMetric: {
    flex: '1 1 45%',
    minWidth: 120,
    backgroundColor: '#ffffff',
    padding: 8,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 5,
  },
  scenarioMetricText: {
    fontSize: 10,
    color: '#2d3748',
  },
  stagesContainer: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  stagesTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#2d3748',
    marginBottom: 6,
  },
  stage: {
    backgroundColor: '#ffffff',
    padding: 6,
    borderRadius: 3,
    borderLeftWidth: 3,
    borderLeftColor: '#38a169',
    marginBottom: 4,
  },
  stageText: {
    fontSize: 10,
    color: '#2d3748',
  },
  pageNumber: {
    position: 'absolute',
    fontSize: 10,
    bottom: 30,
    left: 0,
    right: 0,
    textAlign: 'center',
    color: '#718096',
  },
  header: {
    marginBottom: 30,
    paddingBottom: 20,
    borderBottomWidth: 2,
    borderBottomColor: '#e2e8f0',
  },
});

const PDFDocument: React.FC<PDFDocumentProps> = ({ reportData, reportConfig }) => {
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
    <Document>
      <Page size="A4" style={styles.page}>
        {/* 헤더 */}
        <View style={styles.header}>
          <Text style={styles.title}>
            {reportConfig.customTitle || '성능 테스트 리포트'}
          </Text>
          {reportConfig.companyName && (
            <View style={styles.companyInfo}>
              <Text style={styles.companyName}>{reportConfig.companyName}</Text>
            </View>
          )}
          {reportConfig.reporterName && (
            <View style={styles.companyInfo}>
              <Text style={styles.reporterName}>작성자: {reportConfig.reporterName}</Text>
            </View>
          )}
          <View style={styles.companyInfo}>
            <Text style={styles.reportDate}>
              작성일: {formatDate(new Date().toISOString())}
            </Text>
          </View>
        </View>

        {/* 요약 정보 */}
        {reportConfig.includeExecutiveSummary && (
          <View style={styles.section}>
            <Text style={styles.subtitle}>요약 정보</Text>
            <View style={styles.summaryContainer}>
              <View style={styles.summaryGrid}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>테스트 상태</Text>
                  <Text style={styles.summaryValue}>
                    {reportData.is_completed ? '완료' : '진행 중'}
                  </Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>총 요청 수</Text>
                  <Text style={styles.summaryValue}>{reportData.total_requests}개</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>실패 요청 수</Text>
                  <Text style={styles.summaryValue}>{reportData.failed_requests}개</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>에러율</Text>
                  <Text style={styles.summaryValue}>{formatNumber(reportData.error_rate)}%</Text>
                </View>
              </View>
              {reportConfig.customDescription && (
                <Text style={styles.description}>
                  {reportConfig.customDescription}
                </Text>
              )}
            </View>
          </View>
        )}

        {/* 상세 메트릭 */}
        {reportConfig.includeDetailedMetrics && (
          <View style={styles.section}>
            <Text style={styles.subtitle}>상세 메트릭</Text>
            <View style={styles.metricsGrid}>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>실제 TPS</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.actual_tps)}</Text>
              </View>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>평균 응답시간</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.avg_response_time)}ms</Text>
              </View>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>최대 응답시간</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.max_response_time)}ms</Text>
              </View>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>최소 응답시간</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.min_response_time)}ms</Text>
              </View>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>P95 응답시간</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.p95_response_time)}ms</Text>
              </View>
              <View style={styles.metric}>
                <Text style={styles.metricLabel}>테스트 지속시간</Text>
                <Text style={styles.metricValue}>{formatNumber(reportData.test_duration)}초</Text>
              </View>
            </View>
          </View>
        )}

        {/* 시나리오 분석 */}
        {reportConfig.includeScenarioBreakdown && reportData.scenarios && (
          <View style={styles.section}>
            <Text style={styles.subtitle}>시나리오 분석</Text>
            {reportData.scenarios.map((scenario, index) => (
              <View key={scenario.id} style={styles.scenarioCard}>
                <Text style={styles.scenarioTitle}>
                  시나리오 {index + 1}: {scenario.endpoint.summary}
                </Text>
                
                <View style={styles.endpointInfo}>
                  <Text>{scenario.endpoint.method} {scenario.endpoint.path}</Text>
                </View>
                
                <Text style={styles.scenarioDescription}>
                  {scenario.endpoint.description}
                </Text>
                
                <View style={styles.scenarioMetricsContainer}>
                  <View style={styles.scenarioMetric}>
                    <Text style={styles.scenarioMetricText}>
                      실제 TPS: {formatNumber(scenario.actual_tps)}
                    </Text>
                  </View>
                  <View style={styles.scenarioMetric}>
                    <Text style={styles.scenarioMetricText}>
                      평균 응답시간: {formatNumber(scenario.avg_response_time)}ms
                    </Text>
                  </View>
                  <View style={styles.scenarioMetric}>
                    <Text style={styles.scenarioMetricText}>
                      에러율: {formatNumber(scenario.error_rate)}%
                    </Text>
                  </View>
                  <View style={styles.scenarioMetric}>
                    <Text style={styles.scenarioMetricText}>
                      총 요청: {scenario.total_requests}개
                    </Text>
                  </View>
                </View>

                {scenario.stages && scenario.stages.length > 0 && (
                  <View style={styles.stagesContainer}>
                    <Text style={styles.stagesTitle}>부하 단계</Text>
                    {scenario.stages.map((stage, stageIndex) => (
                      <View key={stage.id} style={styles.stage}>
                        <Text style={styles.stageText}>
                          단계 {stageIndex + 1}: {stage.duration} 동안 {stage.target} VU
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))}
          </View>
        )}

        {/* 페이지 번호 */}
        <Text style={styles.pageNumber} render={({ pageNumber, totalPages }) => (
          `${pageNumber} / ${totalPages}`
        )} fixed />
      </Page>
    </Document>
  );
};

export default PDFDocument;