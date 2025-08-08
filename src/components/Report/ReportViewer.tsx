import React from "react";
import styles from "./ReportViewer.module.css";
import type {TestData, ReportConfig} from "../../pages/Report/Report";
import PDFDocument from "./PDFDocument";
import {PDFViewer} from "@react-pdf/renderer";

interface ReportViewerProps {
  reportData: TestData;
  reportConfig: ReportConfig;
  isPreview?: boolean;
}

const ReportViewer: React.FC<ReportViewerProps> = ({
  reportData,
  reportConfig,
  isPreview = false,
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

  const formatNumber = (num: number, decimals: number = 2) => {
    return num.toFixed(decimals);
  };

  return (
    <div className={styles.container}>
      <div className={styles.actions}></div>

      {isPreview ? (
        <div className={styles.previewContainer}>
          <div className={styles.documentPreview}>
            <div className={styles.documentHeader}>
              <div className="HeadingL">
                {reportConfig.customTitle || "성능 테스트 리포트"}
              </div>
              {reportConfig.companyName && (
                <div className={styles.companyName}>
                  {reportConfig.companyName}
                </div>
              )}
              {reportConfig.reporterName && (
                <div className={styles.reporterName}>
                  작성자: {reportConfig.reporterName}
                </div>
              )}
              <div className={styles.reportDate}>
                작성일: {formatDate(new Date().toISOString())}
                <div className="HeadingS">● Plog</div>
              </div>
            </div>

            {reportConfig.includeExecutiveSummary && (
              <div className={styles.section}>
                <h1 className="HeadingS">1. 요약 정보</h1>
                <div className={styles.sectionContent}>
                  <h2 className="Body">
                    {reportConfig.customDescription || reportData.description || "테스트 설명이 제공되지 않았습니다."}
                  </h2>
                </div>
              </div>
            )}
            <div className={styles.section}>
              <h1 className="HeadingS">2. 테스트 대상 소개 </h1>
              <div className={styles.sectionContent}>
                <h2 className="Body">
                  웹 기반의 CRM 솔루션으로 전신은 Centric-CRM 이며, 공식적으로
                  데이터베이스는 PostgreSQL 8.x를사용하고, 애플리케이션 서버로는
                  Apache Tomcat6.0을 사용함
                </h2>
              </div>
            </div>
            <div className={styles.section}>
              <h1 className="HeadingS">3. 테스트 케이스 및 시나리오 </h1>
              <div className={styles.sectionContent}>
                <h2 className="Body">
                  ConcourseSuite의 신뢰성을 검증하기 위하여 테스트케이스에
                  기반을 둔 기능 테스트와 테스트 시나리오에 기반을 둔 비 기능
                  테스트를 수행한다.
                </h2>
                <h1 className="TitleS">가. 기능별 테스트케이스 현황</h1>
                <h1 className="TitleS">나. 비 기능 테스트 시나리오</h1>
              </div>
            </div>
            <div className={styles.section}>
              <h1 className="HeadingS">4. 기능 테스트 수행 결과</h1>
              <div className={styles.sectionContent}>
                <h2 className="Body">
                  기능 테스트 수행 관련 세부 절차 및 결과는 별첨 ⌜Concoursesuite
                  테스트 케이스⌟를 참고한다.
                </h2>
                <h1 className="TitleS">가. 기능 테스트 결과</h1>
                <h1 className="TitleS">나. 결함 내역</h1>
                <h1 className="TitleS">다. 특이사항</h1>
              </div>
            </div>
            <div className={styles.section}>
              <h1 className="HeadingS">5. 비 기능 테스트 수행 결과 </h1>
              <div className={styles.sectionContent}>
                <h1 className="TitleS">가. 비 기능 테스트 결과</h1>
                <h1 className="TitleS">나. 비 기능 테스트 상세내역</h1>
              </div>
            </div>
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
