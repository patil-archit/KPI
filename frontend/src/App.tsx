import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth";
import { Spinner } from "./lib/ui";
import Login from "./pages/Login";
import Shell from "./components/Shell";
import Launchpad from "./pages/Launchpad";
import Orders from "./pages/Orders";
import Inventory from "./pages/Inventory";
import Maintenance from "./pages/Maintenance";
import Users from "./pages/Users";
import Files from "./pages/Files";
import Scada from "./pages/Scada";
import Engineering from "./pages/Engineering";
import DevMode from "./pages/DevMode";

export default function App() {
  const { user, loading } = useAuth();
  if (loading)
    return <div className="h-screen flex items-center justify-center"><Spinner /></div>;
  if (!user) return (
    <Routes>
      <Route path="/dev" element={<DevMode />} />
      <Route path="*" element={<Login />} />
    </Routes>
  );
  return (
    <Routes>
      <Route path="/dev" element={<DevMode />} />
      <Route element={<Shell />}>
        <Route path="/" element={<Launchpad />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/maintenance" element={<Maintenance />} />
        <Route path="/users" element={<Users />} />
        <Route path="/files" element={<Files />} />
        <Route path="/scada" element={<Scada />} />
        <Route path="/engineering" element={<Engineering />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  );
}
