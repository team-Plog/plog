import React, { useEffect, useState } from "react";
import Header from "../../components/Header/Header";
import styles from "./Test.module.css";
import "../../assets/styles/typography.css";
import { Button } from "../../components/Button/Button";
import {
  Activity,
  CircleAlert,
  Clock,
  RotateCw,
  Timer,
  Users,
} from "lucide-react";
import MetricCard from "../../components/MetricCard/MetricCard";
import MetricChart from "../../components/MetricChart/MetricChart";
import { useLocation } from "react-router-dom";
import { getProjectDetail, getTestHistoryDetail } from "../../api";

const Test: React.FC = () => {
  const location = useLocation();
  const {
    projectId,
    testTitle,
    jobName,
    projectTitle: passedProjectTitle,
    testHistoryId: initialTestHistoryId,
  } = location.state || {};
  const [projectTitle, setProjectTitle] = useState<string>(
    passedProjectTitle || ""
  );
  const [testHistoryId, setTestHistoryId] = useState<number | null>(
    initialTestHistoryId || null
  );

  const [chartData, setChartData] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({
    tps: 0,
    latency: 0,
    error_rate: 0,
    vus: 0,
  });

  useEffect(() => {
    console.log("✅ 선택된 testHistoryId:", testHistoryId);
  }, [testHistoryId]);

  useEffect(() => {
    if (!jobName) return;

    const eventSource = new EventSource(
      `http://35.216.24.11:30002/sse/k6data/${jobName}`
    );

    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        console.log("📡 실시간 k6 데이터:", parsedData);

        const timestamp = new Date(parsedData.timestamp).toLocaleTimeString(
          "ko-KR",
          {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          }
        );

        const overall = parsedData.overall || {
          tps: 0,
          vus: 0,
          response_time: 0,
          error_rate: 0,
        };

        setMetrics({
          tps: overall.tps,
          latency: overall.response_time,
          error_rate: overall.error_rate,
          vus: overall.vus,
        });

        setChartData((prev) =>
          [
            ...prev,
            {
              time: timestamp,
              tps: overall.tps,
              responseTime: overall.response_time,
              errorRate: overall.error_rate,
              users: overall.vus,
            },
          ].slice(-20)
        );
      } catch (e) {
        console.error("⚠️ JSON 파싱 실패:", e);
      }
    };

    eventSource.onerror = (error) => {
      console.error("❌ SSE 연결 오류:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobName]);

  useEffect(() => {
    if (projectId && !passedProjectTitle) {
      getProjectDetail(projectId)
        .then((res) => setProjectTitle(res.data.data.title))
        .catch((err) => {
          console.error("프로젝트 타이틀 불러오기 실패:", err);
          setProjectTitle("프로젝트명 없음");
        });
    }
  }, [projectId, passedProjectTitle]);

  useEffect(() => {
    if (!testHistoryId) return;

    getTestHistoryDetail(testHistoryId)
      .then((res) => {
        console.log("🧪 테스트 상세 정보:", res.data);
      })
      .catch((err) => {
        console.error("❌ 테스트 상세 정보 조회 실패:", err);
      });
  }, [testHistoryId]);

  const chartConfigs = [
    {
      title: "TPS 변화 추이",
      dataKey: "tps",
      color: "#60a5fa",
    },
    {
      title: "평균 응답시간(ms)",
      dataKey: "responseTime",
      color: "#82ca9d",
    },
    {
      title: "에러율(%)",
      dataKey: "errorRate",
      color: "#f87171",
    },
    {
      title: "활성 사용자 수",
      dataKey: "users",
      color: "#8884d8",
    },
  ];

  return (
    <div className={styles.container}>
      <Header testHistoryId={testHistoryId} />
      <div className={styles.content}>
        <header className={styles.header}>
          <div className={styles.headerInner}></div>
        </header>

        <main className={styles.main}>
          <div className={styles.title}>
            <div className="HeadingS">{projectTitle || "프로젝트명 없음"}</div>
            <div className={styles.progress}>
              <div className={styles.status}>
                <div className={styles.statusItem}>
                  <Timer className={styles.icon} />
                  <div className="Body">1분 23초</div>
                </div>
                <div className={styles.statusItem}>
                  <RotateCw className={styles.icon} />
                  <div className="Body">30%</div>
                </div>
              </div>
              <div className={styles.progressButton}>
                <Button variant="primaryGradient">테스트 중단하기</Button>
              </div>
            </div>
          </div>

          <div className={styles.card}>
            <MetricCard
              label="현재 TPS"
              value={metrics.tps?.toLocaleString() || "0"}
              icon={<Activity />}
            />
            <MetricCard
              label="평균 응답시간"
              value={`${metrics.latency?.toFixed(0) || "0"}ms`}
              icon={<Clock />}
            />
            <MetricCard
              label="에러율"
              value={`${metrics.error_rate?.toFixed(1) || "0.0"}%`}
              icon={<CircleAlert />}
            />
            <MetricCard
              label="활성 사용자"
              value={metrics.vus?.toLocaleString() || "0"}
              icon={<Users />}
            />
          </div>

          <div className={styles.chartWrap}>
            {chartConfigs.map((config, index) => (
              <MetricChart
                key={index}
                title={config.title}
                data={chartData}
                dataKey={config.dataKey}
                color={config.color}
              />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Test;