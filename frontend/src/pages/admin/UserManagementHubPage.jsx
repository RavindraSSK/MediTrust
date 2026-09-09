import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext.jsx";
import DashboardShell from "../../components/DashboardShell.jsx";

export default function UserManagementHubPage() {
  const { displayName } = useAuth();
  const navigate = useNavigate();
  return (
    <DashboardShell title="User Management" subtitle="Choose an admin workflow" userLabel={displayName || "Admin"} links={[{ to: "/admin", label: "Back to Dashboard" }]}>
      <section className="panel-box wide-panel">
        <div className="user-management-hub">
          <button className="action-btn" id="pendingRequestsBtn" type="button" onClick={() => navigate("/admin/users/pending")}>Pending Role Requests</button>
          <button className="action-btn" id="registeredUsersBtn" type="button" onClick={() => navigate("/admin/users/registered")}>Registered Users</button>
          <button className="action-btn" id="doctorNurseAssignmentsBtn" type="button" onClick={() => navigate("/admin/users/assignments")}>Doctor-Nurse Assignments</button>
        </div>
      </section>
    </DashboardShell>
  );
}
