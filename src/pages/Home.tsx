import React, { useState } from "react";
import { Plus, Menu } from "lucide-react";
import SearchBar from "../components/SearchBar";
import { colors } from "../assets/colors";

const Home: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: colors.background.primary,
        margin: 0,
        padding: 0,
        width: "100vw",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <header
        style={{
          backgroundColor: colors.background.primary,
          padding: "24px",
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
              gap: "24px",
            }}
          >
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              style={{
                padding: "4px",
                backgroundColor: colors.system.white,
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                transition: "background-color 0.2s",
              }}
            >
              <Menu
                style={{
                  width: "24px",
                  height: "24px",
                  color: colors.system.gray2,
                }}
              />
            </button>
            <h1
              style={{
                fontSize: "16px",
                fontWeight: "bold",
                color: colors.system.black,
                whiteSpace: "nowrap",
                margin: 0,
              }}
            >
              프로젝트 목록
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
                placeholder="입력 내용"
              />
            </div>

            <button
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "linear-gradient(#606060 0%, #000000 100%)",
                color: colors.system.white,
                padding: "8px 16px",
                borderRadius: "8px",
                border: "none",
                whiteSpace: "nowrap",
                cursor: "pointer",
                transition: "background-color 0.2s",
              }}>
              <Plus style={{ width: "16px", height: "16px" }} />
              <span style={{fontSize: 12}}>새 프로젝트 추가하기</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main
        style={{
          maxWidth: "1280px",
          margin: "0 auto",
          padding: "32px 16px",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            textAlign: "center",
            color: colors.system.gray3,
            marginTop: "80px",
          }}
        >
          <p>프로젝트 목록이 여기에 표시됩니다.</p>
        </div>
      </main>
    </div>
  );
};

export default Home;
