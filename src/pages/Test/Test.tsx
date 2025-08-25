import React, {useEffect, useState, useRef} from "react";
import Header from "../../components/Header/Header";
import styles from "./Test.module.css";
import "../../assets/styles/typography.css";
import {Button} from "../../components/Button/Button";
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
import {useLocation} from "react-router-dom";
import {getProjectDetail, getTestHistoryDetail} from "../../api";
import {stopJob} from "../../api/jobScheduler";

const Test: React.FC = () => {
  const location = useLocation();
  const {
    projectId,
    testTitle,
    jobName, // location.state에서 올 수도, 없을 수도 있음
    projectTitle: passedProjectTitle,
    testHistoryId: initialTestHistoryId,
  } = location.state || {};

  const [projectTitle, setProjectTitle] = useState<string>(
    passedProjectTitle || ""
  );
  const [testHistoryId, setTestHistoryId] = useState<number | null>(
    initialTestHistoryId || null
  );

  // 📌 jobName 폴백을 위한 내부 상태 (location.state → 없으면 API job_name)
  const [jobNameState, setJobNameState] = useState<string | null>(
    jobName ?? null
  );
  const effectiveJobName = jobNameState; // 항상 이 값을 사용

  const [chartData, setChartData] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({
    tps: 0,
    latency: 0,
    error_rate: 0,
    vus: 0,
  });

  // 중단 로딩 상태 & SSE 핸들 ref
  const [stopping, setStopping] = useState(false);
  const sseRef = useRef<EventSource | null>(null);
  const [lastJobName, setLastJobName] = useState<string | null>(null);
  const [lastRequestUrl, setLastRequestUrl] = useState<string | null>(null);
  const [scenarioName, setScenarioName] = useState<string | null>(null);

  useEffect(() => {
    console.log("✅ 선택된 testHistoryId:", testHistoryId);
  }, [testHistoryId]);

  // 👉 testHistoryId로 상세 조회해서 job_name 폴백 채우기
  useEffect(() => {
    if (!testHistoryId) return;

    getTestHistoryDetail(testHistoryId)
      .then((res) => {
        console.log("🧪 테스트 상세 정보:", res.data);
        const apiJobName = res?.data?.data?.job_name;
        if (apiJobName && !jobNameState) {
          setJobNameState(apiJobName);
        }
        const apiScenarioName = res?.data?.data?.scenarios?.[0]?.name;
        if (apiScenarioName) {
          setScenarioName(apiScenarioName);
        }
      })
      .catch((err) => {
        console.error("❌ 테스트 상세 정보 조회 실패:", err);
      });
  }, [testHistoryId]); // jobNameState는 의도적으로 의존성 제외(초기 폴백 세팅 목적)

  // 프로젝트 타이틀 불러오기 (필요 시)
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

  // 👉 SSE 연결 (effectiveJobName이 준비되었을 때만)
  useEffect(() => {
    if (!effectiveJobName) return;

    const eventSource = new EventSource(
      `http://35.216.24.11:30002/sse/k6data/${effectiveJobName}`
    );
    sseRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        // console.log("📡 실시간 k6 데이터:", parsedData);

        const timestamp = new Date(parsedData.timestamp).toLocaleTimeString(
          "ko-KR",
          {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hourCycle: "h23",
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
      sseRef.current = null;
    };

    return () => {
      eventSource.close();
      sseRef.current = null;
    };
  }, [effectiveJobName]);

  const handleStopTest = async () => {
    if (!effectiveJobName) {
      alert("jobName이 없어 중단 요청을 보낼 수 없습니다.");
      return;
    }
    try {
      setStopping(true);

      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }

      await stopJob(effectiveJobName);
      alert(`테스트 중단 요청 완료\njob_name: ${effectiveJobName}`);
    } catch (err: any) {
      console.error("테스트 중단 요청 실패:", err?.message);
      console.error("config.url:", err?.config?.baseURL, err?.config?.url);
      alert(`네트워크 오류로 중단 요청 실패\njob_name: ${effectiveJobName}`);
    } finally {
      setStopping(false);
    }
  };

  const combinedSeries = [
    {
      key: "tps",
      name: "현재 TPS",
      color: "#60a5fa",
      unit: "",
      yAxis: "left" as const,
    },
    {
      key: "responseTime",
      name: "평균 응답시간",
      color: "#82ca9d",
      unit: "ms",
      yAxis: "right" as const,
    },
    {
      key: "errorRate",
      name: "에러율",
      color: "#f87171",
      unit: "%",
      yAxis: "right" as const,
    },
    {
      key: "users",
      name: "활성 사용자",
      color: "#8884d8",
      unit: "",
      yAxis: "left" as const,
    },
  ];

  const chartConfigs = [
    {title: "TPS 변화 추이", dataKey: "tps", color: "#60a5fa"},
    {title: "평균 응답시간(ms)", dataKey: "responseTime", color: "#82ca9d"},
    {title: "에러율(%)", dataKey: "errorRate", color: "#f87171"},
    {title: "활성 사용자 수", dataKey: "users", color: "#8884d8"},
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
            <div className="HeadingS">
              {projectTitle || "프로젝트명 없음"}
              {scenarioName && (
                <span className={styles.scenarioName}>({scenarioName})</span>
              )}
            </div>
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
                <Button
                  variant="primaryGradient"
                  onClick={handleStopTest}
                  disabled={stopping || !effectiveJobName}>
                  {stopping ? "중단 요청 중..." : "테스트 중단하기"}
                </Button>
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
            <MetricChart
              title="TPS/평균 응답시간/에러율/활성 사용자"
              data={chartData}
              combinedSeries={combinedSeries}
              height={320}
            />
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
