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

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useLocation } from "react-router-dom";
import { getProjectDetail } from "../../api";

const Test: React.FC = () => {
  const location = useLocation();
  const {
    projectId,
    testTitle,
    jobName,
    projectTitle: passedProjectTitle,
  } = location.state || {};
  const [projectTitle, setProjectTitle] = useState<string>(
    passedProjectTitle || ""
  );

  const [chartData, setChartData] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({
    tps: 0,
    latency: 0,
    error_rate: 0,
    vus: 0,
  });

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
          latency: 0,
          error_rate: 0,
          vus: 0,
        };

        setMetrics(overall); // 메트릭 카드용 데이터 업데이트

        setChartData((prev) => [
          ...prev,
          {
            time: timestamp,
            tps: overall.tps,
            responseTime: overall.latency,
            errorRate: overall.error_rate,
            users: overall.vus,
          },
        ].slice(-20)); // 최근 20개만 유지
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

  return (
    <div className={styles.container}>
      <Header />
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
              value={metrics.tps.toLocaleString()}
              icon={<Activity />}
            />
            <MetricCard
              label="평균 응답시간"
              value={`${metrics.latency.toFixed(0)}ms`}
              icon={<Clock />}
            />
            <MetricCard
              label="에러율"
              value={`${metrics.error_rate.toFixed(1)}%`}
              icon={<CircleAlert />}
            />
            <MetricCard
              label="활성 사용자"
              value={metrics.vus.toLocaleString()}
              icon={<Users />}
            />
          </div>

          <div className={styles.chartWrap}>
            <div className={styles.chart}>
              <h3 className="TitleS">TPS 변화 추이</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="tps" stroke="#60a5fa" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chart}>
              <h3 className="TitleS">평균 응답시간(ms)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="responseTime"
                    stroke="#82ca9d"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chart}>
              <h3 className="TitleS">에러율(%)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="errorRate"
                    stroke="#f87171"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.chart}>
              <h3 className="TitleS">활성 사용자 수</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="users" stroke="#8884d8" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Test;
