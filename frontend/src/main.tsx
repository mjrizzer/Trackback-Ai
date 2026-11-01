import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  Bell,
  ChevronRight,
  GitBranch,
  LogOut,
  Menu,
  Moon,
  ShieldCheck,
  Sun,
} from "lucide-react";
import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import { api } from "./api";
import { Button } from "./components/ui/button";
import "./style.css";

import { ErrorBox } from "./components/common";
import { nav } from "./navigation";
import { Analytics, Reports } from "./pages/Analytics";
import { LoginPage } from "./pages/Authentication";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Evidence";
import { IncidentDetail } from "./pages/Incidents";
import { InvestigationDetail } from "./pages/InvestigationWorkspace";
import { Records } from "./pages/Records";
import { Proposals } from "./pages/Responses";
import { SettingsPage } from "./pages/Settings";
import { client } from "./query";
function App() {
  const [authenticated, setAuthenticated] = useState(
      !!sessionStorage.getItem("traceback-session"),
    ),
    [menu, setMenu] = useState(false),
    [dark, setDark] = useState(
      localStorage.getItem("traceback-theme") === "dark",
    );
  const { data: me, error } = useQuery({
    queryKey: ["me"],
    queryFn: () => api("/me"),
    enabled: authenticated,
    retry: false,
  });
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      sessionStorage.removeItem("traceback-session");
      sessionStorage.removeItem("traceback-token");
      client.clear();
      setAuthenticated(false);
    } catch (e) {
      if (error) {
        sessionStorage.removeItem("traceback-session");
        client.clear();
        setAuthenticated(false);
      } else window.alert((e as Error).message);
    }
  }
  if (!authenticated)
    return (
      <LoginPage
        onLogin={() => {
          client.clear();
          setAuthenticated(true);
        }}
      />
    );
  return (
    <div className={`app ${dark ? "dark" : ""}`}>
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <Link to="/" className="brand">
          <div className="brand-mark">
            <GitBranch size={23} />
          </div>
          traceback<span>AI</span>
        </Link>
        <div className="workspace-tag">
          <span className="workspace-icon">N</span>
          <div>
            <strong>{me?.organization || "Workspace"}</strong>
            <small>Manufacturing workspace</small>
          </div>
          <ChevronRight size={13} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map((n, i) => (
            <React.Fragment key={n.path}>
              {i === 3 && <div className="nav-label">SUPPLY CHAIN</div>}
              {n.path === "/documents" && (
                <div className="nav-label">INTELLIGENCE & GOVERNANCE</div>
              )}
              <NavLink
                to={n.path}
                end={n.path === "/"}
                onClick={() => setMenu(false)}
              >
                <n.icon size={17} />
                <span>{n.title}</span>
              </NavLink>
            </React.Fragment>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="secure-label">
            <ShieldCheck size={15} /> Human-supervised operations
          </div>
          <button onClick={logout}>
            <span className="avatar">
              {me?.user.name
                ?.split(" ")
                .map((s: string) => s[0])
                .join("") || "U"}
            </span>
            <span>
              <strong>{me?.user.name || "User"}</strong>
              <small>{me?.user.role || "Workspace member"}</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      {menu && <div className="sidebar-scrim" onClick={() => setMenu(false)} />}
      <div className="main">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Toggle menu"
            onClick={() => setMenu(!menu)}
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>Industrial intelligence</strong>
          </div>
          <div className="topbar-right">
            <span className="mode-label">
              <span />
              {me?.mode === "live" ? "LIVE AI" : "DEMO MODE"}
            </span>
            <button
              className="icon-button"
              aria-label="Toggle theme"
              onClick={() => {
                setDark(!dark);
                localStorage.setItem(
                  "traceback-theme",
                  !dark ? "dark" : "light",
                );
              }}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link
              to="/proposals"
              className="icon-button"
              aria-label="Review notifications"
            >
              <Bell size={18} />
            </Link>
            <span className="top-avatar">{me?.user.name?.[0] || "U"}</span>
          </div>
        </header>
        <main>
          {error ? (
            <div className="panel">
              <ErrorBox error={error} />
              <Button onClick={logout}>Return to login</Button>
            </div>
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/incidents/:id" element={<IncidentDetail />} />
              <Route
                path="/investigations/:id"
                element={<InvestigationDetail />}
              />
              {[
                "incidents",
                "investigations",
                "suppliers",
                "lots",
                "batches",
                "shipments",
                "customers",
                "inspections",
                "agents",
                "audit",
              ].map((kind) => (
                <Route
                  key={kind}
                  path={`/${kind}`}
                  element={<Records key={kind} kind={kind} />}
                />
              ))}
              <Route path="/documents" element={<Documents />} />
              <Route path="/proposals" element={<Proposals />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
        </main>
        <footer>
          <span>TRACEBACK AI</span>
          <span>Verified evidence. Accountable decisions.</span>
          <span>{me?.organization || "Investigation workspace"}</span>
        </footer>
      </div>
    </div>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
