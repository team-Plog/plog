import React, { useState } from "react";
import { Plus, Menu, PlusCircle } from "lucide-react";
import SearchBar from "../components/SearchBar/SearchBar";
import { Button } from "../components/Button/Button";

const Home: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleNewProject = () => {
    console.log("click Button");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--color-bg-primary)",
        margin: 0,
        padding: 0,
        width: "100vw",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <header
        style={{
          backgroundColor: "var(--color-bg-primary)",
          padding: "var(--spacing-xl)",
          margin: 0,
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
            margin: 0,
            padding: 0,
          }}
        >
          {/* Left Group - Menu and Title */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--spacing-sm)",
            }}
          >
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              style={{
                padding: "var(--spacing-xs)",
                backgroundColor: "var(--color-white)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                transition: "background-color 0.2s",
              }}
            >
              <Menu
                style={{
                  width: "var(--icon-size-md)",
                  height: "var(--icon-size-md)",
                  color: "var(--color-gray-200)",
                }}
              />
            </button>
            <h1
              className="HeadingS"
              style={{
                color: "var(--color-black)",
                whiteSpace: 'nowrap',
                margin: 0,
              }}
            >
              내 프로젝트
            </h1>
          </div>

          {/* Right Group - Search Bar and Button */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "60px",
            }}
          >
            <div style={{ width: "300px" }}>
              <SearchBar
                value={searchTerm}
                onChange={setSearchTerm}
                placeholder="검색어를 입력하세요"
              />
            </div>

            <Button 
              variant="primaryGradient" 
              onClick={handleNewProject}
            >
              <Plus style={{ width: "var(--icon-size-md)", height: "var(--icon-size-md)" }} />
              새 프로젝트 추가하기
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "32px var(--spacing-lg)",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        {/* Empty State Container */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "400px",
            backgroundColor: "var(--color-gray-100)",
            border: "1px solid var(--color-border-primary)",
            borderRadius: "var(--radius-lg)",
            padding: "64px",
            gap: "64px",
          }}
        >
          {/* Icon Container */}
          <div
            style={{
              width: "200px",
              height: "160px",
              background: "linear-gradient(180deg, rgba(0, 0, 0, 0.07) 0%, rgba(0, 0, 0, 0.03) 100%)",
              border: "1px solid var(--color-border-primary)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 15px 0 rgba(0, 0, 0, 0.04) inset",
            }}
          >
            <PlusCircle
              style={{
                width: "48px",
                height: "48px",
                color: "rgba(0, 0, 0, 0.1)",
              }}
            />
          </div>

          {/* Text Content */}
          <div
            style={{
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              gap: "var(--spacing-sm)",
            }}
          >
            <p
              className="HeadingS"
              style={{
                color: "var(--color-black)",
                margin: 0,
              }}
            >
              아직 생성된 프로젝트가 없습니다
            </p>
            <p
              className="Body"
              style={{
                color: "var(--color-gray-300)",
                margin: 0,
              }}
            >
              부하 테스트를 시작하려면 새로운 프로젝트를 생성하세요.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;