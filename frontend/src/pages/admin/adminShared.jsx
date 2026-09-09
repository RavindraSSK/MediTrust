import { useCallback, useState } from "react";

import { errorMessage } from "../../lib/format.js";

export const ROLES = ["Doctor", "Nurse", "Admin"];

export function userName(row) {
  return row.full_name || [row.first_name, row.last_name].filter(Boolean).join(" ") || "Unknown";
}

export function sortNewestFirst(rows) {
  return [...rows].sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
}

export function matchesUser(row, query) {
  if (!query) return true;
  return `${userName(row)} ${row.email} ${row.role} ${row.role_status}`.toLowerCase().includes(query.toLowerCase());
}

/** Shared admin panel state: search, status message, load/perform helpers. */
export function useAdminPanel(loader) {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState({ text: "", error: false });

  const load = useCallback(
    async (successMessage = "Loaded.") => {
      setMessage({ text: "Loading...", error: false });
      try {
        const data = await loader();
        setRows(data);
        setMessage({ text: successMessage, error: false });
        return data;
      } catch (error) {
        setMessage({ text: errorMessage(error, "Unable to load data."), error: true });
        return null;
      }
    },
    [loader]
  );

  const perform = useCallback(
    async (action, successMessage) => {
      setMessage({ text: "Saving changes...", error: false });
      try {
        await action();
        await load(successMessage);
      } catch (error) {
        setMessage({ text: errorMessage(error, "Unable to save changes."), error: true });
      }
    },
    [load]
  );

  return { rows, setRows, query, setQuery, message, load, perform };
}

export function AdminPanel({ title, message, onRefresh, searchPlaceholder, query, onQueryChange, children }) {
  return (
    <section className="panel-box wide-panel admin-management-panel" id="adminManagementPanel">
      <div className="admin-panel-header">
        <div>
          <h2>{title}</h2>
          <p id="adminManagementMessage" className={`admin-message${message.error ? " admin-message-error" : ""}`}>{message.text}</p>
        </div>
        <button className="mini-btn" id="refreshAdminUsersBtn" type="button" onClick={onRefresh}>Refresh</button>
      </div>
      {searchPlaceholder ? (
        <input id="adminSearchInput" className="admin-search" type="search" placeholder={searchPlaceholder} value={query} onChange={(event) => onQueryChange(event.target.value)} />
      ) : null}
      {children}
    </section>
  );
}
