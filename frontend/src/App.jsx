import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Scanner from "./pages/Scanner";
import Trades from "./pages/Trades";
import PositionSizer from "./pages/PositionSizer";
import Backtest from "./pages/Backtest";
import Compounder from "./pages/Compounder";
import Allocation from "./pages/Allocation";
import Deployment from "./pages/Deployment";
import Watchlist from "./pages/Watchlist";
import Advisor from "./pages/Advisor";
import RiskDashboard from "./pages/RiskDashboard";

const PAGES = {
  dashboard: Dashboard,
  risk: RiskDashboard,
  advisor: Advisor,
  deployment: Deployment,
  scanner: Scanner,
  watchlist: Watchlist,
  trades: Trades,
  sizer: PositionSizer,
  backtest: Backtest,
  compounder: Compounder,
  allocation: Allocation,
};

export default function App() {
  const [page, setPage] = useState("dashboard");
  const PageComponent = PAGES[page] || Dashboard;

  return (
    <div className="flex h-screen overflow-hidden bg-base">
      <Sidebar active={page} onNavigate={setPage} />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1440px] mx-auto p-6">
          <PageComponent />
        </div>
      </main>
    </div>
  );
}
