import { $, go } from "../utils.js";
import { PAGE_LOGIN } from "../config.js";
import { registerUser } from "../services/api.js";

export function initSignupPage() {
  const form = $("signupForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const first = ($("firstName")?.value || "").trim();
    const last = ($("lastName")?.value || "").trim();
    const email = ($("email")?.value || "").trim();
    const pass = ($("password")?.value || "").trim();
    const conf = ($("confirmPassword")?.value || "").trim();

    if (!first || !last || !email || !pass || !conf) {
      alert("Please fill all fields.");
      return;
    }

    if (pass !== conf) {
      alert("Passwords do not match.");
      return;
    }

    try {
      const out = await registerUser(`${first} ${last}`, email, pass);

      if (!out.ok) {
        alert(out.message);
        return;
      }

      alert(out.message);
      go(PAGE_LOGIN);
    } catch (err) {
      alert("Registration failed: " + (err?.message || err));
    }
  });
}