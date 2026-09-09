import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { clearSession, getStoredToken, getStoredUser, storeSession } from "../api/client.js";
import { fetchMe, loginUser } from "../api/endpoints.js";

const AuthContext = createContext(null);

function normalizeUser(user) {
  if (!user || typeof user !== "object") return null;
  const firstName = String(user.first_name || "").trim();
  const lastName = String(user.last_name || "").trim();
  const fullName = String(user.full_name || [firstName, lastName].filter(Boolean).join(" ")).trim();
  return {
    ...user,
    first_name: firstName || (fullName ? fullName.split(/\s+/)[0] : ""),
    last_name: lastName || (fullName ? fullName.split(/\s+/).slice(1).join(" ") : ""),
    full_name: fullName,
    email: String(user.email || "").trim(),
    role: String(user.role || "").trim(),
  };
}

export function dashboardPathForRole(role) {
  if (role === "Doctor") return "/doctor";
  if (role === "Nurse") return "/nurse";
  if (role === "Admin") return "/admin";
  return "/assessment";
}

export function displayName(user) {
  if (!user) return "";
  return [user.first_name, user.last_name].filter(Boolean).join(" ").trim() || user.full_name || user.email || "";
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStoredToken());
  const [user, setUser] = useState(() => normalizeUser(getStoredUser()));
  // Tracks the live token so an in-flight profile refresh cannot resurrect a session after logout.
  const tokenRef = useRef(token);

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  const logout = useCallback(() => {
    tokenRef.current = "";
    clearSession();
    setToken("");
    setUser(null);
  }, []);

  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("meditrust:unauthorized", handler);
    return () => window.removeEventListener("meditrust:unauthorized", handler);
  }, [logout]);

  // Re-validate the stored session once on load so revoked/expired tokens sign out cleanly.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchMe()
      .then((profile) => {
        if (cancelled || tokenRef.current !== token) return;
        const normalized = normalizeUser(profile);
        setUser(normalized);
        storeSession(token, normalized);
      })
      .catch((error) => {
        if (!cancelled && (error.status === 401 || error.status === 403)) logout();
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password);
    if (!data.ok || !data.access_token) {
      return { ok: false, message: data.message || "Invalid email or password." };
    }
    const normalized = normalizeUser(data.user || data);
    storeSession(data.access_token, normalized);
    setToken(data.access_token);
    setUser(normalized);
    return { ok: true, user: normalized };
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      displayName: displayName(user),
      dashboardPath: dashboardPathForRole(user?.role),
    }),
    [user, token, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}

/** Route guard: requires a signed-in user, optionally with one of the given roles. */
export function RequireAuth({ roles, children }) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }
  if (roles && roles.length && !roles.includes(user.role)) {
    return <Navigate to={dashboardPathForRole(user.role)} replace />;
  }
  return children;
}
