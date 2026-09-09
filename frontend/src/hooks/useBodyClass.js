import { useEffect } from "react";

/** Applies legacy page-level body classes (login-page, dashboard-page, assessment-page). */
export function useBodyClass(className) {
  useEffect(() => {
    const classes = className.split(/\s+/).filter(Boolean);
    document.body.classList.add(...classes);
    return () => document.body.classList.remove(...classes);
  }, [className]);
}
