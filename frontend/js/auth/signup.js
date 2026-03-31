import { renderPasswordRules } from "./password-rules.js";

const API_BASE = "http://127.0.0.1:8000";

export function initSignupPage() {
  const signupForm = document.getElementById("signupForm");
  const signupMessage = document.getElementById("signupMessage");
  const passwordInput = document.getElementById("password");
  const rulesBox = document.getElementById("passwordRules");

  if (!signupForm) return;

  passwordInput?.addEventListener("input", () => {
    renderPasswordRules(rulesBox, passwordInput.value);
  });

  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    signupMessage.textContent = "";

    const fullName = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const role = document.getElementById("role").value.trim();
    const hospitalName = document.getElementById("hospitalName").value.trim();
    const password = document.getElementById("password").value.trim();
    const confirmPassword = document.getElementById("confirmPassword").value.trim();

    if (!fullName || !email || !role || !password || !confirmPassword) {
      signupMessage.textContent = "Please complete all required fields.";
      return;
    }

    if (password.length < 8) {
      signupMessage.textContent = "Password must be at least 8 characters.";
      return;
    }

    if (password !== confirmPassword) {
      signupMessage.textContent = "Passwords do not match.";
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          role,
          hospital_name: hospitalName
        })
      });

      const data = await response.json();

      if (!data.ok) {
        signupMessage.textContent = data.message || "Registration failed.";
        return;
      }

      alert("Account created successfully. Please log in.");
      window.location.href = "index.html";
    } catch (error) {
      signupMessage.textContent = "Unable to connect to the server. Please try again.";
    }
  });
}