import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home/Home";
import ProjectDetail from "./pages/ProjectDetail/ProjectDetail";
import Test from "./pages/Test/Test";


function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/projectDetail" element={<ProjectDetail />} />
        <Route path="/test" element={<Test />} />
      </Routes>
    </Router>
  )
}

export default App
