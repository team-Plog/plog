import React, {useEffect, useState, useRef, useMemo} from "react";
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
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import MetricCard from "../../components/MetricCard/MetricCard";
import MetricChart from "../../components/MetricChart/MetricChart";
import {useLocation} from "react-router-dom";
import {
  getProjectDetail,
  getTestHistoryDetail,
  getSseK6DataUrl,
} from "../../api";
import {stopJob} from "../../api/jobScheduler";

type Point = {
  time: string;
  tps: number;
  responseTime: number;
  errorRate: number;
  users: number;
};

const OVERALL = "__OVERALL__";

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

  // jobName 폴백
  const [jobNameState, setJobNameState] = useState<string | null>(
    jobName ?? null
  );
  const effectiveJobName = jobNameState;

  const [chartData, setChartData] = useState<Point[]>([]);
  const [metrics, setMetrics] = useState({
    tps: 0,
    latency: 0,
    error_rate: 0,
    vus: 0,
  });

  // 시나리오별 상태
  const [scenarioChartData, setScenarioChartData] = useState<
    Record<string, Point[]>
  >({});
  const [scenarioMetrics, setScenarioMetrics] = useState<
    Record<
      string,
      {tps: number; latency: number; error_rate: number; vus: number}
    >
  >({});

  // 캐러셀 상태
  const scenarioNames = Object.keys(scenarioChartData);
  const slides = useMemo(() => [OVERALL, ...scenarioNames], [scenarioNames]);
  const [slideIndex, setSlideIndex] = useState(0);
  const currentSlide = slides[slideIndex] || null;

  const goPrev = () => {
    if (slides.length === 0) return;
    setSlideIndex((i) => (i - 1 + slides.length) % slides.length);
  };
  const goNext = () => {
    if (slides.length === 0) return;
    setSlideIndex((i) => (i + 1) % slides.length);
  };
  const slideLabel = (name: string) => (name === OVERALL ? "전체" : `${name}`);

  // 중단 로딩 & SSE
  const [stopping, setStopping] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // testHistoryId로 job_name만 폴백
  useEffect(() => {
    if (!testHistoryId) return;
    getTestHistoryDetail(testHistoryId)
      .then((res) => {
        const apiJobName = res?.data?.data?.job_name;
        if (apiJobName && !jobNameState) {
          setJobNameState(apiJobName);
        }
      })
      .catch((err) => {
        console.error("❌ 테스트 상세 정보 조회 실패:", err);
      });
  }, [testHistoryId]);

  // 프로젝트 타이틀
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

  // SSE 연결
  useEffect(() => {
    if (!effectiveJobName) return;

    const sseUrl = getSseK6DataUrl(effectiveJobName);
    const eventSource = new EventSource(sseUrl);
    sseRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);

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

        // 전체 메트릭/차트
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

        // 시나리오별
        const scenarios = Array.isArray(parsedData.scenarios)
          ? parsedData.scenarios
          : [];
        if (scenarios.length > 0) {
          setScenarioChartData((prev) => {
            const next: Record<string, Point[]> = {...prev};
            scenarios.forEach((sc: any) => {
              const name = sc?.name ?? "unknown";
              const point: Point = {
                time: timestamp,
                tps: sc?.tps ?? 0,
                responseTime: sc?.response_time ?? 0,
                errorRate: sc?.error_rate ?? 0,
                users: sc?.vus ?? 0,
              };
              const arr = next[name] ? [...next[name], point] : [point];
              next[name] = arr.slice(-20);
            });
            return next;
          });

          setScenarioMetrics((prev) => {
            const next = {...prev};
            scenarios.forEach((sc: any) => {
              const name = sc?.name ?? "unknown";
              next[name] = {
                tps: sc?.tps ?? 0,
                latency: sc?.response_time ?? 0,
                error_rate: sc?.error_rate ?? 0,
                vus: sc?.vus ?? 0,
              };
            });
            return next;
          });
        }
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

  // 슬라이드 안전화
  useEffect(() => {
    if (slides.length === 0) {
      setSlideIndex(0);
      return;
    }
    if (slideIndex >= slides.length) {
      setSlideIndex(slides.length - 1);
    }
  }, [slides.length]);

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
                <Button
                  variant="primaryGradient"
                  onClick={handleStopTest}
                  disabled={stopping || !effectiveJobName}>
                  {stopping ? "중단 요청 중..." : "테스트 중단하기"}
                </Button>
              </div>
            </div>
          </div>

          {/* 전체 + 시나리오 캐러셀 */}
          {slides.length > 0 && (
            <section className={styles.scenarioSection}>
              <div className={styles.scenarioHeader}>
                <div className={styles.carouselControls}>
                  <button
                    type="button"
                    onClick={goPrev}
                    disabled={slides.length <= 1}
                    className={styles.arrowButton}>
                    <ChevronLeft />
                  </button>
                  <div
                    className="HeadingS"
                    style={{minWidth: 160, textAlign: "center"}}>
                    {currentSlide ? slideLabel(currentSlide) : "데이터 없음"}
                    {slides.length > 1 && (
                      <span className="CaptionLight" style={{marginLeft: 8}}>
                        {slideIndex + 1} / {slides.length}
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={goNext}
                    disabled={slides.length <= 1}
                    className={styles.arrowButton}>
                    <ChevronRight />
                  </button>
                </div>
              </div>

              {currentSlide && (
                <div className={styles.scenarioBlock}>
                  <div className={styles.card}>
                    {currentSlide === OVERALL ? (
                      <>
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
                      </>
                    ) : (
                      <>
                        <MetricCard
                          label="현재 TPS"
                          value={
                            scenarioMetrics[
                              currentSlide
                            ]?.tps?.toLocaleString() || "0"
                          }
                          icon={<Activity />}
                        />
                        <MetricCard
                          label="평균 응답시간"
                          value={`${
                            scenarioMetrics[currentSlide]?.latency?.toFixed(
                              0
                            ) || "0"
                          }ms`}
                          icon={<Clock />}
                        />
                        <MetricCard
                          label="에러율"
                          value={`${
                            scenarioMetrics[currentSlide]?.error_rate?.toFixed(
                              1
                            ) || "0.0"
                          }%`}
                          icon={<CircleAlert />}
                        />
                        <MetricCard
                          label="활성 사용자"
                          value={
                            scenarioMetrics[
                              currentSlide
                            ]?.vus?.toLocaleString() || "0"
                          }
                          icon={<Users />}
                        />
                      </>
                    )}
                  </div>

                  {/* 그래프 */}
                  <div className={styles.chartWrap}>
                    <MetricChart
                      title={`${slideLabel(currentSlide)} `}
                      data={
                        currentSlide === OVERALL
                          ? chartData
                          : scenarioChartData[currentSlide] || []
                      }
                      combinedSeries={combinedSeries}
                      height={300}
                    />
                    {chartConfigs.map((config, idx) => (
                      <MetricChart
                        key={`${currentSlide}-${idx}`}
                        title={`${slideLabel(currentSlide)} ${config.title}`}
                        data={
                          currentSlide === OVERALL
                            ? chartData
                            : scenarioChartData[currentSlide] || []
                        }
                        dataKey={config.dataKey}
                        color={config.color}
                      />
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
};

export default Test;
