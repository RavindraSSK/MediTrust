import { useCallback, useEffect, useState } from "react";

import { createDoctorNurseAssignment, deleteDoctorNurseAssignment, fetchAdminUsers, fetchDoctorNurseAssignments } from "../../api/endpoints.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import DashboardShell from "../../components/DashboardShell.jsx";
import { formatDateTime } from "../../lib/format.js";
import { AdminPanel, sortNewestFirst, useAdminPanel, userName } from "./adminShared.jsx";

function matchesAssignment(row, query) {
  if (!query) return true;
  return `${row.doctor_name} ${row.doctor_email} ${row.nurse_name} ${row.nurse_email}`.toLowerCase().includes(query.toLowerCase());
}

export default function AssignmentsPage() {
  const { displayName } = useAuth();
  const [users, setUsers] = useState([]);
  const loader = useCallback(async () => {
    const [userRows, assignmentRows] = await Promise.all([fetchAdminUsers(), fetchDoctorNurseAssignments()]);
    setUsers(userRows);
    return assignmentRows;
  }, []);
  const { rows, query, setQuery, message, load, perform } = useAdminPanel(loader);
  const [doctorId, setDoctorId] = useState("");
  const [nurseId, setNurseId] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    load("Assignments loaded.");
  }, [load]);

  const doctors = sortNewestFirst(users.filter((row) => row.role === "Doctor" && row.role_status === "approved"));
  const nurses = sortNewestFirst(users.filter((row) => row.role === "Nurse" && row.role_status === "approved"));
  const visible = [...rows]
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0) || (Number(b.id) || 0) - (Number(a.id) || 0))
    .filter((row) => matchesAssignment(row, query.trim()));

  const handleAssign = (event) => {
    event.preventDefault();
    setFormError("");
    if (!doctorId || !nurseId) {
      setFormError("Select both a doctor and a nurse.");
      return;
    }
    perform(() => createDoctorNurseAssignment(doctorId, nurseId), "Nurse assigned to doctor.");
  };

  return (
    <DashboardShell fixed title="Doctor-Nurse Assignments" subtitle="Assign nurses to one or more doctors" userLabel={displayName || "Admin"} links={[{ to: "/admin/users", label: "Back to User Management" }]}>
      <AdminPanel title="Assignments" message={formError ? { text: formError, error: true } : message} onRefresh={() => load("Assignments refreshed.")} searchPlaceholder="Search by doctor or nurse name/email" query={query} onQueryChange={setQuery}>
        <form id="assignmentForm" className="assignment-form" onSubmit={handleAssign}>
          <select id="doctorSelect" className="admin-select" value={doctorId} onChange={(event) => setDoctorId(event.target.value)} required>
            <option value="">Select doctor</option>
            {doctors.map((row) => (
              <option key={row.id} value={row.id}>{userName(row)}</option>
            ))}
          </select>
          <select id="nurseSelect" className="admin-select" value={nurseId} onChange={(event) => setNurseId(event.target.value)} required>
            <option value="">Select nurse</option>
            {nurses.map((row) => (
              <option key={row.id} value={row.id}>{userName(row)}</option>
            ))}
          </select>
          <button className="action-btn" id="assignNurseBtn" type="submit">Assign Nurse</button>
        </form>
        <div className="admin-table-wrap admin-scroll-list">
          <table className="admin-table">
            <thead>
              <tr><th>Doctor</th><th>Nurse</th><th>Assigned</th><th>Actions</th></tr>
            </thead>
            <tbody id="assignmentsTable">
              {!visible.length ? (
                <tr><td colSpan={4}>{query.trim() ? "No matching users found." : "No doctor-nurse assignments yet."}</td></tr>
              ) : (
                visible.map((row) => (
                  <tr key={row.id}>
                    <td>{row.doctor_name}<br /><span>{row.doctor_email}</span></td>
                    <td>{row.nurse_name}<br /><span>{row.nurse_email}</span></td>
                    <td>{formatDateTime(row.created_at)}</td>
                    <td><button className="mini-btn admin-row-btn unassign-btn" type="button" onClick={() => perform(() => deleteDoctorNurseAssignment(row.id), "Nurse unassigned from doctor.")}>Unassign</button></td>
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
