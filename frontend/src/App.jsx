import { useState, useEffect, createContext, useContext } from "react";
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
import Geopolitics from "./pages/Geopolitics";
import PaperTrading from "./pages/PaperTrading";
import AlgoTrading from "./pages/AlgoTrading";
import { updateCapital as apiUpdateCapital } from "./api";

export const CapitalContext = createContext({ capital: 20000, setCapital: () => {} });
export const useCapital = () => useContext(CapitalContext);

const PAGES = {
  dashboard: Dashboard,
  risk: RiskDashboard,
  advisor: Advisor,
  deployment: Deployment,
  scanner: Scanner,
  watchlist: Watchlist,
  geopolitics: Geopolitics,
  trades: Trades,
  paper: PaperTrading,
  algos: AlgoTrading,
  sizer: PositionSizer,
  backtest: Backtest,
  compounder: Compounder,
  allocation: Allocation,
};

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [capital, setCapitalState] = useState(() => {
    const saved = localStorage.getItem("stonks_capital");
    return saved ? parseFloat(saved) : 20000;
  });

  const setCapital = (value) => {
    const num = parseFloat(value);
    if (!isNaN(num) && num >= 1000) {
      setCapitalState(num);
      localStorage.setItem("stonks_capital", String(num));
      apiUpdateCapital(num).catch(() => {});
    }
  };

  const PageComponent = PAGES[page] || Dashboard;

  return (
    <CapitalContext.Provider value={{ capital, setCapital }}>
      <div className="flex h-screen overflow-hidden bg-base">
        <Sidebar active={page} onNavigate={setPage} capital={capital} setCapital={setCapital} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1440px] mx-auto p-6">
            <PageComponent />
          </div>
        </main>
      </div>
    </CapitalContext.Provider>
  );
}
