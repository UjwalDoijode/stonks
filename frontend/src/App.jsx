import { useState, useEffect, createContext, useContext } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Scanner from "./pages/Scanner";
import Trades from "./pages/Trades";
import Backtest from "./pages/Backtest";
import Advisor from "./pages/Advisor";
import RiskDashboard from "./pages/RiskDashboard";
import AlgoTrading from "./pages/AlgoTrading";
import AIChat from "./pages/AIChat";
import News from "./pages/News";
import { updateCapital as apiUpdateCapital } from "./api";

export const CapitalContext = createContext({ capital: 20000, setCapital: () => {} });
export const useCapital = () => useContext(CapitalContext);

const PAGES = {
  dashboard: Dashboard,
  ai: AIChat,
  scanner: Scanner,
  advisor: Advisor,
  risk: RiskDashboard,
  algos: AlgoTrading,
  trades: Trades,
  backtest: Backtest,
  news: News,
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
