import React from "react";
import {BrowserRouter as Router, Routes, Route} from "react-router-dom";
import Home from "./pages/Home/Home";
import ProjectDetail from "./pages/ProjectDetail/ProjectDetail";
import Test from "./pages/Test/Test";
import TestList from "./pages/TestList/TestList";
import Report from "./pages/Report/Report";
import Infrastructure from "./pages/Infrastructure/Infrastructure";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/projectDetail" element={<ProjectDetail />} />
        <Route path="/test" element={<Test />} />
        <Route path="/testList" element={<TestList />} />
        <Route path="/report" element={<Report />} />
        <Route path="/infrastructure" element={<Infrastructure />} />
      </Routes>
    </Router>
  );
}

export default App;
