import React from "react";
import Header from "../../components/Header/Header";
import styles from "./Test.module.css";
import "../../assets/styles/typography.css";
import {Button} from "../../components/Button/Button";
import {Activity, CircleAlert, Clock, RotateCw, Timer, Users} from "lucide-react";
import MetricCard from "../../components/MetricCard/MetricCard";

const Test: React.FC = () => {
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
              <MetricCard
                label="현재 TPS"
                value="1,165"
                icon={<Activity />}
              />
              <MetricCard
                label="평균 응답시간"
                value="156ms"
                icon={<Clock />}
              />
              <MetricCard
                label="에러율"
                value="2.3%"
                icon={<CircleAlert />}
              />
              <MetricCard
                label="활성 사용자"
                value="450"
                icon={<Users />}
              />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Test;