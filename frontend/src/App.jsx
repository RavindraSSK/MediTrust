import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { RequireAuth } from "./auth/AuthContext.jsx";
import AdminDashboardPage from "./pages/AdminDashboardPage.jsx";
import AssessmentPage from "./pages/AssessmentPage.jsx";
import ChangePasswordPage from "./pages/ChangePasswordPage.jsx";
import DemoPreviewPage from "./pages/DemoPreviewPage.jsx";
import DoctorDashboardPage from "./pages/DoctorDashboardPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ModelCardPage from "./pages/ModelCardPage.jsx";
import NurseDashboardPage from "./pages/NurseDashboardPage.jsx";
import PatientsPage from "./pages/PatientsPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import AssignmentsPage from "./pages/admin/AssignmentsPage.jsx";
import PendingRequestsPage from "./pages/admin/PendingRequestsPage.jsx";
import RegisteredUsersPage from "./pages/admin/RegisteredUsersPage.jsx";
import UserManagementHubPage from "./pages/admin/UserManagementHubPage.jsx";

const CLINICAL = ["Doctor", "Nurse", "Admin"];

// Old static-site URLs keep working (nginx serves index.html for unknown paths).
const LEGACY_PATHS = {
  "/index.html": "/",
  "/signup.html": "/signup",
  "/meditrust.html": "/assessment",
  "/patients.html": "/patients",
  "/doctor-dashboard.html": "/doctor",
  "/nurse-dashboard.html": "/nurse",
  "/admin-dashboard.html": "/admin",
  "/forgot-password.html": "/forgot-password",
  "/reset-password.html": "/reset-password",
  "/change-password.html": "/change-password",
  "/demo-coming-soon.html": "/demo",
  "/admin/users/index.html": "/admin/users",
  "/admin/users/pending-requests/index.html": "/admin/users/pending",
  "/admin/users/registered-users/index.html": "/admin/users/registered",
  "/admin/users/doctor-nurse-assignments/index.html": "/admin/users/assignments",
};

function LegacyRedirect() {
  const location = useLocation();
  const target = LEGACY_PATHS[location.pathname.toLowerCase()] || "/";
  return <Navigate to={{ pathname: target, search: location.search }} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/demo" element={<DemoPreviewPage />} />

      <Route path="/assessment" element={<RequireAuth roles={CLINICAL}><AssessmentPage /></RequireAuth>} />
      <Route path="/patients" element={<RequireAuth roles={CLINICAL}><PatientsPage /></RequireAuth>} />
      <Route path="/model" element={<RequireAuth roles={CLINICAL}><ModelCardPage /></RequireAuth>} />
      <Route path="/change-password" element={<RequireAuth><ChangePasswordPage /></RequireAuth>} />

      <Route path="/doctor" element={<RequireAuth roles={["Doctor", "Admin"]}><DoctorDashboardPage /></RequireAuth>} />
      <Route path="/nurse" element={<RequireAuth roles={["Nurse", "Admin"]}><NurseDashboardPage /></RequireAuth>} />

      <Route path="/admin" element={<RequireAuth roles={["Admin"]}><AdminDashboardPage /></RequireAuth>} />
      <Route path="/admin/users" element={<RequireAuth roles={["Admin"]}><UserManagementHubPage /></RequireAuth>} />
      <Route path="/admin/users/pending" element={<RequireAuth roles={["Admin"]}><PendingRequestsPage /></RequireAuth>} />
      <Route path="/admin/users/registered" element={<RequireAuth roles={["Admin"]}><RegisteredUsersPage /></RequireAuth>} />
      <Route path="/admin/users/assignments" element={<RequireAuth roles={["Admin"]}><AssignmentsPage /></RequireAuth>} />

      <Route path="*" element={<LegacyRedirect />} />
    </Routes>
  );
}
