import { useEffect } from "react";

import { fetchAdminUsers, updateAdminUserRoleStatus } from "../../api/endpoints.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import DashboardShell from "../../components/DashboardShell.jsx";
import { AdminPanel, matchesUser, sortNewestFirst, useAdminPanel, userName } from "./adminShared.jsx";

export default function PendingRequestsPage() {
  const { user, displayName } = useAuth();
  const panel = useAdminPanel(fetchAdminUsers);
  const { rows, query, setQuery, message, load, perform } = panel;

  useEffect(() => {
    load("Pending requests loaded.");
  }, [load]);

  const pending = sortNewestFirst(rows).filter((row) => row.role_status === "pending").filter((row) => matchesUser(row, query.trim()));
  const isSelf = (row) => row.email === user?.email || row.id === user?.id;

  return (
    <DashboardShell fixed title="Pending Role Requests" subtitle="Review and approve requested access" userLabel={displayName || "Admin"} links={[{ to: "/admin/users", label: "Back to User Management" }]}>
      <AdminPanel title="Pending Requests" message={message} onRefresh={() => load("Pending requests refreshed.")} searchPlaceholder="Search by name, email, or requested role" query={query} onQueryChange={setQuery}>
        <div className="admin-table-wrap admin-scroll-list">
          <table className="admin-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Requested Role</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody id="pendingUsersTable">
              {!pending.length ? (
                <tr><td colSpan={5}>{query.trim() ? "No matching users found." : "No pending role requests."}</td></tr>
              ) : (
                pending.map((row) => (
                  <tr key={row.id}>
                    <td>{userName(row)}</td>
                    <td>{row.email}</td>
                    <td>{row.role}</td>
                    <td><span className={`status-pill status-${row.role_status || "approved"}`}>{row.role_status || "approved"}</span></td>
                    <td>
                      <div className="admin-action-row">
                        <button className="mini-btn admin-row-btn approve-user-btn" type="button" disabled={isSelf(row)} onClick={() => perform(() => updateAdminUserRoleStatus(row.id, "approved"), "Role request approved.")}>Approve</button>
                        <button className="mini-btn admin-row-btn reject-user-btn" type="button" disabled={isSelf(row)} onClick={() => perform(() => updateAdminUserRoleStatus(row.id, "rejected"), "Role request rejected.")}>Reject</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </AdminPanel>
    </DashboardShell>
  );
}
