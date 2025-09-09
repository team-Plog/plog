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
  getTestHistoryTimeseries,
  getSseK6DataUrl,
} from "../../api";
import {stopJob} from "../../api/jobScheduler";

type Point = {
  time: string;
  tps: number;
  responseTime: number;
  errorRate: number;
  users: number;
  p95ResponseTime?: number;
  p99ResponseTime?: number;
};

const OVERALL = "__OVERALL__";

const Test: React.FC = () => {
  const location = useLocation();
  const {
    projectId,
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

  // 테스트 완료 상태
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // jobName 콜백
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
    p95: 0,
    p99: 0,
  });

  // 시나리오별 상태
  const [scenarioChartData, setScenarioChartData] = useState<
    Record<string, Point[]>
  >({});
  const [scenarioMetrics, setScenarioMetrics] = useState<
    Record<
      string,
      {
        tps: number;
        latency: number;
        error_rate: number;
        vus: number;
        p95: number;
        p99: number;
      }
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

  // testHistoryId로 상세 정보 및 완료 상태 확인
  useEffect(() => {
    if (!testHistoryId) {
      setIsLoading(false);
      return;
    }

    getTestHistoryDetail(testHistoryId)
      .then((res) => {
        const data = res?.data?.data;
        const apiJobName = data?.job_name;
        const completed = data?.is_completed;

        if (apiJobName && !jobNameState) {
          setJobNameState(apiJobName);
        }

        setIsCompleted(completed || false);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("테스트 상세 정보 조회 실패:", err);
        setIsLoading(false);
      });
  }, [testHistoryId]);

  // 완료된 테스트의 시계열 데이터 로드
  useEffect(() => {
    if (!testHistoryId || !isCompleted || isLoading) return;

    getTestHistoryTimeseries(testHistoryId)
      .then((res) => {
        const data = res?.data?.data;

        if (data?.overall?.data) {
          // 전체 데이터 변환
          const overallPoints: Point[] = data.overall.data.map((item: any) => ({
            time: new Date(item.timestamp).toLocaleTimeString("ko-KR", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hourCycle: "h23",
            }),
            tps: item.tps || 0,
            responseTime: item.avg_response_time || 0,
            errorRate: item.error_rate || 0,
            users: item.vus || 0,
            p95ResponseTime: item.p95_response_time || 0,
            p99ResponseTime: item.p99_response_time || 0,
          }));

          setChartData(overallPoints);

          // 최신 메트릭 설정
          const latestOverall = data.overall.data[data.overall.data.length - 1];
          if (latestOverall) {
            setMetrics({
              tps: latestOverall.tps || 0,
              latency: latestOverall.avg_response_time || 0,
              error_rate: latestOverall.error_rate || 0,
              vus: latestOverall.vus || 0,
              p95: latestOverall.p95_response_time || 0,
              p99: latestOverall.p99_response_time || 0,
            });
          }
        }

        if (data?.scenarios && Array.isArray(data.scenarios)) {
          // 시나리오별 데이터 변환
          const newScenarioChartData: Record<string, Point[]> = {};
          const newScenarioMetrics: Record<string, any> = {};

          data.scenarios.forEach((scenario: any) => {
            const scenarioName = scenario.scenario_name || "unknown";

            if (scenario.data && Array.isArray(scenario.data)) {
              const points: Point[] = scenario.data.map((item: any) => ({
                time: new Date(item.timestamp).toLocaleTimeString("ko-KR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hourCycle: "h23",
                }),
                tps: item.tps || 0,
                responseTime: item.avg_response_time || 0,
                errorRate: item.error_rate || 0,
                users: item.vus || 0,
                p95ResponseTime: item.p95_response_time || 0,
                p99ResponseTime: item.p99_response_time || 0,
              }));

              newScenarioChartData[scenarioName] = points;

              // 최신 메트릭
              const latestScenario = scenario.data[scenario.data.length - 1];
              if (latestScenario) {
                newScenarioMetrics[scenarioName] = {
                  tps: latestScenario.tps || 0,
                  latency: latestScenario.avg_response_time || 0,
                  error_rate: latestScenario.error_rate || 0,
                  vus: latestScenario.vus || 0,
                  p95: latestScenario.p95_response_time || 0,
                  p99: latestScenario.p99_response_time || 0,
                };
              }
            }
          });

          setScenarioChartData(newScenarioChartData);
          setScenarioMetrics(newScenarioMetrics);
        }
      })
      .catch((err) => {
        console.error("시계열 데이터 로드 실패:", err);
      });
  }, [testHistoryId, isCompleted, isLoading]);

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

  // 실시간 SSE 연결 (완료되지 않은 테스트만)
  useEffect(() => {
    if (!effectiveJobName || isCompleted || isLoading) return;

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
          p95_response_time: 0,
          p99_response_time: 0,
        };

        // 전체 메트릭/차트
        setMetrics({
          tps: overall.tps,
          latency: overall.response_time,
          error_rate: overall.error_rate,
          vus: overall.vus,
          p95: overall.p95_response_time || 0,
          p99: overall.p99_response_time || 0,
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
              p95ResponseTime: overall.p95_response_time || 0,
              p99ResponseTime: overall.p99_response_time || 0,
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
                p95ResponseTime: sc?.p95_response_time ?? 0,
                p99ResponseTime: sc?.p99_response_time ?? 0,
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
                p95: sc?.p95_response_time ?? 0,
                p99: sc?.p99_response_time ?? 0,
              };
            });
            return next;
          });
        }
      } catch (e) {
        console.error("JSON 파싱 실패:", e);
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE 연결 오류:", error);
      eventSource.close();
      sseRef.current = null;
    };

    return () => {
      eventSource.close();
      sseRef.current = null;
    };
  }, [effectiveJobName, isCompleted, isLoading]);

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

  // P95, P99 데이터가 있는지 확인 (완료된 테스트에서만 사용 가능)
  const hasPercentileData = isCompleted;

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
    ...(hasPercentileData
      ? [
          {
            key: "p95ResponseTime",
            name: "P95 응답시간",
            color: "#fb8e8e",
            unit: "ms",
            yAxis: "right" as const,
          },
          {
            key: "p99ResponseTime",
            name: "P99 응답시간",
            color: "#000000",
            unit: "ms",
            yAxis: "right" as const,
          },
        ]
      : []),
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
    ...(hasPercentileData
      ? [
          {
            title: "P95 응답시간(ms)",
            dataKey: "p95ResponseTime",
            color: "#fbbf24",
          },
          {
            title: "P99 응답시간(ms)",
            dataKey: "p99ResponseTime",
            color: "#f97316",
          },
        ]
      : []),
    {title: "에러율(%)", dataKey: "errorRate", color: "#f87171"},
    {title: "활성 사용자 수", dataKey: "users", color: "#8884d8"},
  ];

  if (isLoading) {
    return (
      <div className={styles.container}>
        <Header testHistoryId={testHistoryId} />
        <div className={styles.content}>
          <main className={styles.main}>
            <div className="HeadingS">데이터 로딩 중...</div>
          </main>
        </div>
      </div>
    );
  }

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
                  <div className="Body">
                    {isCompleted ? "완료됨" : "1분 23초"}
                  </div>
                </div>
                <div className={styles.statusItem}>
                  <RotateCw className={styles.icon} />
                  <div className="Body">{isCompleted ? "100%" : "30%"}</div>
                </div>
              </div>
              {!isCompleted && (
                <div className={styles.progressButton}>
                  <Button
                    variant="primaryGradient"
                    onClick={handleStopTest}
                    disabled={stopping || !effectiveJobName}>
                    {stopping ? "중단 요청 중..." : "테스트 중단하기"}
                  </Button>
                </div>
              )}
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
                      title={`${slideLabel(currentSlide)} 종합 지표`}
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
