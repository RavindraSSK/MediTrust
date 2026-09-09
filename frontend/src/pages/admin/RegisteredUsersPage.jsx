import { useEffect } from "react";

import { deleteAdminUser, fetchAdminUsers, updateAdminUserRole } from "../../api/endpoints.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import DashboardShell from "../../components/DashboardShell.jsx";
import { AdminPanel, ROLES, matchesUser, sortNewestFirst, useAdminPanel, userName } from "./adminShared.jsx";

const UNIVERSAL_ADMIN_EMAIL = "meditrust@gmail.com";

export default function RegisteredUsersPage() {
  const { user, displayName } = useAuth();
  const { rows, query, setQuery, message, load, perform } = useAdminPanel(fetchAdminUsers);

  useEffect(() => {
    load("Registered users loaded.");
  }, [load]);

  const visible = sortNewestFirst(rows).filter((row) => matchesUser(row, query.trim()));
  const isSelf = (row) => row.email === user?.email || row.id === user?.id;
  const isUniversalAdmin = (row) => (row.email || "").toLowerCase().trim() === UNIVERSAL_ADMIN_EMAIL;

  const handleDelete = (row) => {
    if (!window.confirm(`Delete ${row.email || "this user"}? This cannot be undone.`)) return;
    perform(() => deleteAdminUser(row.id), "User account deleted.");
  };

  return (
    <DashboardShell fixed title="Registered Users" subtitle="Manage accounts and assigned roles" userLabel={displayName || "Admin"} links={[{ to: "/admin/users", label: "Back to User Management" }]}>
      <AdminPanel title="Registered Users" message={message} onRefresh={() => load("Registered users refreshed.")} searchPlaceholder="Search by name, email, or role" query={query} onQueryChange={setQuery}>
        <div className="admin-table-wrap admin-scroll-list">
          <table className="admin-table">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody id="registeredUsersTable">
              {!visible.length ? (
                <tr><td colSpan={5}>{query.trim() ? "No matching users found." : "No registered users found."}</td></tr>
              ) : (
                visible.map((row) => (
                  <tr key={row.id}>
                    <td>{userName(row)}</td>
                    <td>{row.email}</td>
                    <td>{row.role}</td>
                    <td><span className={`status-pill status-${row.role_status || "approved"}`}>{row.role_status || "approved"}</span></td>
                    <td>
                      <div className="admin-action-row">
                        <select
                          className="admin-select role-change-select"
                          value={row.role}
                          disabled={isSelf(row) || isUniversalAdmin(row)}
                          onChange={(event) => perform(() => updateAdminUserRole(row.id, event.target.value), "User role updated.")}
                        >
                          {ROLES.map((role) => (
                            <option key={role} value={role}>{role}</option>
                          ))}
                        </select>
                        <button className="mini-btn admin-row-btn delete-user-btn" type="button" disabled={isSelf(row) || isUniversalAdmin(row)} onClick={() => handleDelete(row)}>Delete</button>
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
