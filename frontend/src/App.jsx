import React from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import Header from "./components/Header/Header";
import InteractionPanel from "./components/InteractionPanel/InteractionPanel";
import ChatPanel from "./components/ChatPanel/ChatPanel";
import ToastStack from "./components/common/Toast";
import ResizableSplit from "./components/common/ResizableSplit";
import "./App.css";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-shell__main">
        <Header />
        <ResizableSplit left={<InteractionPanel />} right={<ChatPanel />} />
      </div>
      <ToastStack />
    </div>
  );
}
