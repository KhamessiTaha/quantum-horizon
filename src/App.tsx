import { Route, Routes } from "react-router-dom";
import Header from "./components/Header.tsx";
import Landing from "./pages/Landing.tsx";
import Viewer from "./pages/Viewer.tsx";

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/view" element={<Viewer />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </>
  );
}
