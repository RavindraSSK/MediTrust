import { storeCurrentUser } from "./session.js?v=20260701a";
import { attachPasswordToggle } from "./password-toggle.js?v=20260701a";
import { loginUser } from "../services/api.js?v=20260701a";

export function initLoginPage() {
  const loginForm = document.getElementById("loginForm");
  const loginBtn = document.getElementById("loginBtn");
  const loginMessage = document.getElementById("loginMessage");
  const passwordInput = document.getElementById("password");
  const demoBtn = document.querySelector(".explore-demo");

  if (!loginForm || !loginBtn || !passwordInput) return;

  attachPasswordToggle("password", "togglePassword", "eyeOpenIcon", "eyeClosedIcon");

  if (demoBtn) {
    demoBtn.addEventListener("click", () => {
      window.location.href = "demo-coming-soon.html";
    });
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (loginMessage) loginMessage.textContent = "";

    const email = document.getElementById("email")?.value.trim();
    const password = passwordInput.value.trim();

    if (!email || !password) {
      if (loginMessage) {
        loginMessage.textContent = "Please enter your work email and password.";
      }
      return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = "Signing In...";

    try {
      const data = await loginUser(email, password);

      if (!data.ok) {
        if (loginMessage) {
          loginMessage.textContent = data.message || "Invalid email or password.";
        }
        loginBtn.disabled = false;
        loginBtn.textContent = "Sign In";
        return;
      }

      storeCurrentUser(data);

      if (data.role === "Doctor") {
        window.location.href = "doctor-dashboard.html";
      } else if (data.role === "Nurse") {
        window.location.href = "nurse-dashboard.html";
      } else if (data.role === "Admin") {
        window.location.href = "admin-dashboard.html";
      } else {
        window.location.href = "meditrust.html";
      }
    } catch (error) {
      if (loginMessage) {
        loginMessage.textContent = "Unable to connect to the server. Please try again.";
      }
      loginBtn.disabled = false;
      loginBtn.textContent = "Sign In";
    }
  });
}
