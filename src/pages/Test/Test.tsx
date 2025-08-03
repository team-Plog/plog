import React from "react";
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

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const Test: React.FC = () => {
  const chartData = [
    {time: "00:00", tps: 800, responseTime: 140, errorRate: 1.2, users: 300},
    {time: "00:10", tps: 1200, responseTime: 150, errorRate: 1.5, users: 350},
    {time: "00:20", tps: 1500, responseTime: 160, errorRate: 2.3, users: 400},
    {time: "00:30", tps: 1000, responseTime: 170, errorRate: 2.8, users: 420},
    {time: "00:40", tps: 1165, responseTime: 156, errorRate: 2.3, users: 450},
  ];

  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.content}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerInner}></div>
        </header>

        {/* Main Content */}
        <main className={styles.main}>
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
          <div className={styles.card}>
            <MetricCard label="현재 TPS" value="1,165" icon={<Activity />} />
            <MetricCard label="평균 응답시간" value="156ms" icon={<Clock />} />
            <MetricCard label="에러율" value="2.3%" icon={<CircleAlert />} />
            <MetricCard label="활성 사용자" value="450" icon={<Users />} />
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
                  <Line type="monotone" dataKey="errorRate" stroke="#f87171" />
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
