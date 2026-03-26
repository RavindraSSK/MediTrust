import { $, go } from "../utils.js";
import { PAGE_MEDI } from "../config.js";
import { loginUser } from "../services/api.js";
import { setLoggedIn } from "./session.js";

export function initLoginPage() {
  const form = $("loginForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = ($("email")?.value || "").trim();
    const pass = ($("password")?.value || "").trim();

    if (!email || !pass) {
      alert("Enter email and password.");
      return;
    }

    try {
      const out = await loginUser(email, pass);

      if (!out.ok) {
        alert(out.message);
        return;
      }

      setLoggedIn(true, email);
      go(PAGE_MEDI);
    } catch (err) {
      alert("Login failed: " + (err?.message || err));
    }
  });
}