import {
  renderPasswordRules,
  isPasswordValid,
  getPasswordValidationMessage,
} from "./password-rules.js?v=20260418f";
import { attachPasswordToggle } from "./password-toggle.js?v=20260418f";
import { registerUser } from "../services/api.js?v=20260418f";

export function initSignupPage() {
  const signupForm = document.getElementById("signupForm");
  const signupMessage = document.getElementById("signupMessage");
  const passwordInput = document.getElementById("password");
  const rulesBox = document.getElementById("passwordRules");

  if (!signupForm) return;

  attachPasswordToggle("password", "toggleSignupPassword", "signupEyeOpenIcon", "signupEyeClosedIcon");
  attachPasswordToggle("confirmPassword", "toggleSignupConfirmPassword", "signupConfirmEyeOpenIcon", "signupConfirmEyeClosedIcon");

  passwordInput?.addEventListener("input", () => {
    renderPasswordRules(rulesBox, passwordInput.value);
  });

  renderPasswordRules(rulesBox, passwordInput?.value || "");

  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    signupMessage.textContent = "";

    const firstName = document.getElementById("firstName").value.trim();
    const lastName = document.getElementById("lastName").value.trim();
    const email = document.getElementById("email").value.trim();
    const role = document.getElementById("role").value.trim();
    const hospitalName = document.getElementById("hospitalName").value.trim();
    const password = document.getElementById("password").value.trim();
    const confirmPassword = document.getElementById("confirmPassword").value.trim();

    if (!firstName || !lastName || !email || !role || !password || !confirmPassword) {
      signupMessage.textContent = "Please complete all required fields.";
      return;
    }

    if (!isPasswordValid(password)) {
      signupMessage.textContent = getPasswordValidationMessage(password);
      return;
    }

    if (password !== confirmPassword) {
      signupMessage.textContent = "Passwords do not match.";
      return;
    }

    try {
      const data = await registerUser(
        firstName,
        lastName,
        email,
        password,
        role,
        hospitalName
      );

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
