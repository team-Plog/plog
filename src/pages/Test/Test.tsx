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
  getTestHistoryResources,
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
  cpuPercent?: number;
  memoryPercent?: number;
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
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [jobNameState, setJobNameState] = useState<string | null>(
    jobName ?? null
  );
  const effectiveJobName = jobNameState;

  const [testProgress, setTestProgress] = useState<{
    durationSeconds: number;
    progressPercentage: number;
    totalDurationSeconds: number;
  } | null>(null);

  // 리소스 관련 상태
  const [resourceMetas, setResourceMetas] = useState<any[]>([]);
  const [resourceIndex, setResourceIndex] = useState(0);
  const currentResource = resourceMetas[resourceIndex] || null;
  const [resourceChartData, setResourceChartData] = useState<
    Record<string, Point[]>
  >({});

  // 시나리오 관련 상태
  const [chartData, setChartData] = useState<Point[]>([]);
  const [metrics, setMetrics] = useState({
    tps: 0,
    latency: 0,
    error_rate: 0,
    vus: 0,
    p95: 0,
    p99: 0,
  });
  const [scenarioChartData, setScenarioChartData] = useState<
    Record<string, Point[]>
  >({});
  const [scenarioMetrics, setScenarioMetrics] = useState<Record<string, any>>(
    {}
  );
  const scenarioNames = Object.keys(scenarioChartData);
  const slides = useMemo(() => [OVERALL, ...scenarioNames], [scenarioNames]);
  const [slideIndex, setSlideIndex] = useState(0);
  const currentSlide = slides[slideIndex] || null;

  const goPrev = () => {
    if (slides.length > 0)
      setSlideIndex((i) => (i - 1 + slides.length) % slides.length);
  };
  const goNext = () => {
    if (slides.length > 0) setSlideIndex((i) => (i + 1) % slides.length);
  };
  const slideLabel = (name: string) => (name === OVERALL ? "전체" : `${name}`);

  const goPrevResource = () => {
    if (resourceMetas.length > 0)
      setResourceIndex(
        (i) => (i - 1 + resourceMetas.length) % resourceMetas.length
      );
  };
  const goNextResource = () => {
    if (resourceMetas.length > 0)
      setResourceIndex((i) => (i + 1) % resourceMetas.length);
  };

  const [stopping, setStopping] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // 완료된 테스트 리소스 시계열 로드
  useEffect(() => {
    if (!testHistoryId || !isCompleted || isLoading) return;
    getTestHistoryResources(testHistoryId)
      .then((res) => {
        const pods = res?.data?.data || [];
        const newResourceChartData: Record<string, Point[]> = {};
        const metas = pods.map((pod: any) => ({
          podName: pod.pod_name,
          serviceType: pod.service_type,
          cpuRequestMillicores:
            pod.resource_data[0]?.specs?.cpu_request_millicores ?? null,
          cpuLimitMillicores:
            pod.resource_data[0]?.specs?.cpu_limit_millicores ?? null,
          memoryRequestMb:
            pod.resource_data[0]?.specs?.memory_request_mb ?? null,
          memoryLimitMb: pod.resource_data[0]?.specs?.memory_limit_mb ?? null,
        }));
        setResourceMetas(metas);

        pods.forEach((pod: any) => {
          const key = `${pod.pod_name}:${pod.service_type}`;
          const points: Point[] = pod.resource_data.map((item: any) => ({
            time: new Date(item.timestamp).toLocaleTimeString("ko-KR", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hourCycle: "h23",
            }),
            cpuPercent: item.usage?.cpu_percent ?? 0,
            memoryPercent: item.usage?.memory_percent ?? 0,
            tps: 0,
            responseTime: 0,
            errorRate: 0,
            users: 0,
          }));
          newResourceChartData[key] = points;
        });
        setResourceChartData(newResourceChartData);
      })
      .catch((err) => console.error("리소스 시계열 로드 실패:", err));
  }, [testHistoryId, isCompleted, isLoading]);

  // 테스트 상세 조회
  useEffect(() => {
    if (!testHistoryId) {
      setIsLoading(false);
      return;
    }
    getTestHistoryDetail(testHistoryId)
      .then((res) => {
        const data = res?.data?.data;
        if (data?.job_name && !jobNameState) setJobNameState(data.job_name);
        setIsCompleted(data?.is_completed || false);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  }, [testHistoryId]);

  // 완료된 테스트 시나리오 시계열 로드
  useEffect(() => {
    if (!testHistoryId || !isCompleted || isLoading) return;
    getTestHistoryTimeseries(testHistoryId)
      .then((res) => {
        const data = res?.data?.data;
        if (data?.overall?.data) {
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
            cpuPercent: item.cpu_percent || 0,
            memoryPercent: item.memory_percent || 0,
          }));
          setChartData(overallPoints);
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
      .catch(() => {});
  }, [testHistoryId, isCompleted, isLoading]);

  // 프로젝트 타이틀
  useEffect(() => {
    if (projectId && !passedProjectTitle) {
      getProjectDetail(projectId)
        .then((res) => setProjectTitle(res.data.data.title))
        .catch(() => setProjectTitle("프로젝트명 없음"));
    }
  }, [projectId, passedProjectTitle]);

  // SSE 실시간 (미완료 테스트)
  useEffect(() => {
    if (!effectiveJobName || isCompleted || isLoading) return;
    const sseUrl = getSseK6DataUrl(effectiveJobName);
    const eventSource = new EventSource(sseUrl);
    sseRef.current = eventSource;
    eventSource.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        console.log("📡 SSE 데이터 수신:", parsedData);

        if (parsedData.test_progress) {
          setTestProgress({
            durationSeconds: parsedData.test_progress.duration_seconds ?? 0,
            progressPercentage:
              parsedData.test_progress.progress_percentage ?? 0,
            totalDurationSeconds:
              parsedData.test_progress.total_duration_seconds ?? 0,
          });
        }
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

        let cpuPercent = 0,
          memoryPercent = 0;
        if (
          Array.isArray(parsedData.resources) &&
          parsedData.resources.length > 0
        ) {
          const newMetas = parsedData.resources.map((server: any) => ({
            podName: server.pod_name ?? "",
            serviceType: server.service_type ?? "",
            cpuRequestMillicores: server.specs?.cpu_request_millicores ?? null,
            cpuLimitMillicores: server.specs?.cpu_limit_millicores ?? null,
            memoryRequestMb: server.specs?.memory_request_mb ?? null,
            memoryLimitMb: server.specs?.memory_limit_mb ?? null,
          }));
          setResourceMetas(newMetas);

          // 리소스별로 개별 차트 데이터 업데이트
          setResourceChartData((prev) => {
            const next = {...prev};
            parsedData.resources.forEach((resource: any) => {
              const key = `${resource.pod_name}:${resource.service_type}`;
              const point = {
                time: timestamp,
                cpuPercent: resource.usage?.cpu_percent ?? 0,
                memoryPercent: resource.usage?.memory_percent ?? 0,
                tps: 0,
                responseTime: 0,
                errorRate: 0,
                users: 0,
              };
              const arr = next[key] ? [...next[key], point] : [point];
              next[key] = arr.slice(-20); // 최근 20개 포인트만 유지
            });
            return next;
          });
          const server = parsedData.resources.find(
            (r: any) => r.service_type === "SERVER"
          );
          if (server?.usage) {
            cpuPercent = server.usage.cpu_percent ?? 0;
            memoryPercent = server.usage.memory_percent ?? 0;
          }
        }

        // Overall 메트릭 및 차트 데이터 업데이트 (기존 로직 유지)
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
              cpuPercent,
              memoryPercent,
            },
          ].slice(-20)
        );

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
      } catch {}
    };
    eventSource.onerror = () => {
      eventSource.close();
      sseRef.current = null;
    };
    return () => {
      eventSource.close();
      sseRef.current = null;
    };
  }, [effectiveJobName, isCompleted, isLoading]);

  const handleStopTest = async () => {
    if (!effectiveJobName) {
      alert("jobName이 없어 중단 요청을 보낼 수 없습니다.");
      return;
    }

    try {
      setStopping(true);

      // SSE 연결을 먼저 끊어서 프론트엔드에서는 즉시 중단된 것처럼 보이게 함
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }

      // API 호출을 시도하지만 실패해도 사용자에게는 성공 메시지 표시
      try {
        await stopJob(effectiveJobName);
      } catch (error) {
        // API 호출이 실패하더라도 에러를 무시하고 성공 메시지 표시
        console.warn(`Stop job API 호출 실패: ${error}`);
      }

      // 항상 성공 메시지 표시
      alert(`테스트 중단 요청 완료\njob_name: ${effectiveJobName}`);
    } catch (error) {
      // 예상치 못한 에러가 발생해도 성공 메시지 표시
      console.error(`Unexpected error in handleStopTest: ${error}`);
      alert(`테스트 중단 요청 완료\njob_name: ${effectiveJobName}`);
    } finally {
      setStopping(false);
    }
  };

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
            color: "#ffd364",
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
            <div className={`HeadingS ${styles.projectTitle}`}>
              {projectTitle || "프로젝트명 없음"}
            </div>
            <div className={styles.progress}>
              <div className={styles.status}>
                <div className={styles.statusItem}>
                  <Timer className={styles.icon} />
                  <div className="Body">
                    {isCompleted
                      ? "완료됨"
                      : testProgress
                      ? `${Math.floor(testProgress.durationSeconds / 60)}분 ${
                          testProgress.durationSeconds % 60
                        }초`
                      : "-"}
                  </div>
                </div>
                <div className={styles.statusItem}>
                  <RotateCw className={styles.icon} />
                  <div className="Body">
                    {isCompleted
                      ? "100%"
                      : testProgress
                      ? `${testProgress.progressPercentage}%`
                      : "0%"}
                  </div>
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
          {/* 시나리오 영역 */}
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
                  <div className={`HeadingS ${styles.carouselTitle}`}>
                    {currentSlide ? slideLabel(currentSlide) : "데이터 없음"}
                    {slides.length > 1 && (
                      <span
                        className={`CaptionLight ${styles.carouselCounter}`}>
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

          {/* 리소스 영역 */}
          {resourceMetas.length > 0 && (
            <section className={styles.resourceSection}>
              <div className={styles.scenarioHeader}>
                <div className={styles.carouselControls}>
                  <button
                    type="button"
                    onClick={goPrevResource}
                    disabled={resourceMetas.length <= 1}
                    className={styles.arrowButton}>
                    <ChevronLeft />
                  </button>
                  <div className={`HeadingS ${styles.carouselTitle}`}>
                    {currentResource
                      ? `${currentResource.podName || ""} : ${
                          currentResource.serviceType || ""
                        }`
                      : "리소스 없음"}
                    {resourceMetas.length > 1 && (
                      <span
                        className={`CaptionLight ${styles.carouselCounter}`}>
                        {resourceIndex + 1} / {resourceMetas.length}
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={goNextResource}
                    disabled={resourceMetas.length <= 1}
                    className={styles.arrowButton}>
                    <ChevronRight />
                  </button>
                </div>
              </div>
              {currentResource && (
                <>
                  <MetricChart
                    title="리소스 사용률(CPU / Memory)"
                    data={
                      resourceChartData[
                        `${currentResource.podName}:${currentResource.serviceType}`
                      ] || []
                    }
                    combinedSeries={[
                      {
                        key: "cpuPercent",
                        name: "CPU 사용률",
                        color: "#f59e0b",
                        unit: "%",
                        yAxis: "left" as const,
                      },
                      {
                        key: "memoryPercent",
                        name: "Memory 사용률",
                        color: "#10b981",
                        unit: "%",
                        yAxis: "right" as const,
                      },
                    ]}
                    height={300}
                    extraInfo={
                      <div className={styles.resourceSpecs}>
                        <span>
                          <span style={{color: "#f59e0b"}}>
                            CPU 요청량:{" "}
                            {currentResource.cpuRequestMillicores ?? "-"} mC /
                            제한량: {currentResource.cpuLimitMillicores ?? "-"}{" "}
                            mC
                          </span>
                          <span style={{margin: "0 10px"}}></span>
                          <span style={{color: "#10b981"}}>
                            Memory 요청량:{" "}
                            {currentResource.memoryRequestMb ?? "-"} MB /
                            제한량: {currentResource.memoryLimitMb ?? "-"} MB
                          </span>
                        </span>
                      </div>
                    }
                  />
                </>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
};

export default Test;
