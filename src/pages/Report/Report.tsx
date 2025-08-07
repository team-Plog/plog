import React, {useEffect, useState} from "react";
import styles from "./Report.module.css";
import "../../assets/styles/typography.css";
import Header from "../../components/Header/Header";
import {useLocation} from "react-router-dom";
import {getTestHistoryDetail} from "../../api";

const Report: React.FC = () => {
  const location = useLocation();
  const {testHistoryId, projectId} = location.state || {};
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!testHistoryId) {
      setError("testHistoryId가 전달되지 않았습니다.");
      setLoading(false);
      return;
    }

    const fetchReportData = async () => {
      try {
        const res = await getTestHistoryDetail(testHistoryId);
        setReportData(res.data.data); // API 응답 데이터로 상태를 업데이트합니다.
        console.log("✅ 테스트 리포트 데이터:", res.data.data);
      } catch (err) {
        console.error("❌ 테스트 리포트 정보 조회 실패:", err);
        setError("리포트 정보를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [testHistoryId]);

  if (loading) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <h1 className="HeadingM">📄 테스트 리포트</h1>
          <p className="Body">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Header />
        <div className={styles.content}>
          <h1 className="HeadingM">📄 테스트 리포트</h1>
          <p className="Body" style={{color: "red"}}>
            {error}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        <div className="HeadingS">테스트 리포트</div>
        <p className="Body">
          프로젝트 ID: {projectId ?? "없음"} / 테스트 히스토리 ID:{" "}
          {testHistoryId ?? "없음"}
        </p>
      </div>
    </div>
  );
};

export default Report;
